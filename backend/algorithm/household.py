import random
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import monotonic
from .base import Algorithm, Change

# Záloha pro starší konfigurace bez household.schedule.
DEFAULT_HOUSEHOLD_SCHEDULE = (
    {"time": "04:00", "percent": 10, "end_percent": 50},
    {"time": "05:00", "percent": 70},
    {"time": "06:00", "percent": 50},
    {"time": "08:00", "percent": 5},
    {"time": "19:00", "percent": 70},
    {"time": "21:00", "percent": 70, "end_percent": 40},
    {"time": "23:00", "percent": 10},
)


class HouseholdSchedule:
    """Daily cyclic intervals; optional end_percent makes an interval linear."""
    def __init__(self, entries=None):
        entries = DEFAULT_HOUSEHOLD_SCHEDULE if entries is None else entries
        if not isinstance(entries, (list, tuple)) or not entries:
            raise ValueError("household.schedule musí být neprázdný seznam.")
        self.points = []
        for index, entry in enumerate(entries, 1):
            try:
                if not isinstance(entry, dict) or set(entry) - {"time", "percent", "end_percent"}:
                    raise ValueError
                time_text = entry["time"]
                if not isinstance(time_text, str):
                    raise ValueError
                parts = time_text.split(":")
                if (len(parts) != 2 or not all(part.isascii() and part.isdigit() for part in parts)
                        or len(parts[0]) not in (1, 2) or len(parts[1]) != 2):
                    raise ValueError
                hour, minute = map(int, parts)
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    raise ValueError
                values = [entry["percent"], entry.get("end_percent", entry["percent"])]
                if any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not math.isfinite(value) or not 0 <= value <= 100 for value in values):
                    raise ValueError
                self.points.append((hour * 3600 + minute * 60, *values))
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"household.schedule: položka {index} potřebuje time ve formátu HH:MM "
                                 "a percent (případně end_percent) od 0 do 100.") from None
        self.points.sort()
        if len({point[0] for point in self.points}) != len(self.points):
            raise ValueError("household.schedule obsahuje duplicitní čas.")

    def ratio(self, now):
        second = now.hour * 3600 + now.minute * 60 + now.second + now.microsecond / 1_000_000
        for index in range(len(self.points) - 1, -1, -1):
            if self.points[index][0] <= second:
                break
        else:
            index = len(self.points) - 1
        start, percent, end_percent = self.points[index]
        end = self.points[(index + 1) % len(self.points)][0]
        duration = (end - start) % 86400 or 86400
        elapsed = (second - start) % 86400
        return (percent + (end_percent - percent) * elapsed / duration) / 100


def household_ratio(now: datetime) -> float:
    """Default schedule, retained for callers without explicit configuration."""
    return HouseholdSchedule().ratio(now)


@dataclass
class _HouseholdState:
    on_since: float | None = None
    deadline: float | None = None
    off_since: float = -math.inf


class HouseholdLighting(Algorithm):
    """One coordinator for every household light, with real-time dwell limits."""
    identifier = "domacnost"
    shared = True
    time_required = False

    @staticmethod
    def name() -> str:
        return "Domácnost"

    def __init__(self, min_on_seconds=30, max_on_seconds=300, min_off_seconds=30, schedule=None):
        try:
            limits = tuple(float(value) for value in (min_on_seconds, max_on_seconds, min_off_seconds))
        except (TypeError, ValueError):
            raise ValueError("Časy domácnosti musí být kladná čísla.") from None
        if not all(math.isfinite(value) and value > 0 for value in limits) or limits[0] > limits[1]:
            raise ValueError("Časy domácnosti musí být kladné a minimum svícení nesmí překročit maximum.")
        self.min_on_seconds, self.max_on_seconds, self.min_off_seconds = limits
        self.schedule = HouseholdSchedule(schedule)
        self._states = {}
        self._outputs = {}

    def reset(self):
        self._states.clear()
        self._outputs = {}

    def forget(self, item_id):
        self._states.pop(item_id, None)

    def evaluate(self, item_ids, now):
        elapsed = monotonic()
        members = dict.fromkeys(item_ids)
        self._states = {item_id: self._states.get(item_id, _HouseholdState()) for item_id in members}
        target = math.floor(len(members) * self.schedule.ratio(now) + 0.5) if now is not None else 0

        def turn_off(state):
            state.on_since = state.deadline = None
            state.off_since = elapsed

        # Random deadlines guarantee rotation even when the target stays constant.
        for state in self._states.values():
            if state.on_since is not None and elapsed >= state.deadline:
                turn_off(state)

        active = [state for state in self._states.values() if state.on_since is not None]
        excess = max(0, len(active) - target)
        # A falling target never cuts an automatic on-period below its minimum.
        eligible_to_stop = sorted(
            (state for state in active if elapsed - state.on_since >= self.min_on_seconds),
            key=lambda state: state.on_since,
        )
        for state in eligible_to_stop[:excess]:
            turn_off(state)

        active_count = sum(state.on_since is not None for state in self._states.values())
        eligible_to_start = [state for state in self._states.values()
                             if state.on_since is None and elapsed - state.off_since >= self.min_off_seconds]
        # Prefer lights that have been off longest; randomize ties such as startup.
        random.shuffle(eligible_to_start)
        eligible_to_start.sort(key=lambda state: state.off_since)
        for state in eligible_to_start[:max(0, target - active_count)]:
            state.on_since = elapsed
            state.deadline = elapsed + random.uniform(self.min_on_seconds, self.max_on_seconds)

        return {item_id: int(state.on_since is not None) for item_id, state in self._states.items()}

    def prepare(self, item_ids, now):
        self._outputs = self.evaluate(item_ids, now)

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        return self._outputs[item_id]

    def forecast(self, item_id, now, sunrise, sunset, speed, source, real_now, elapsed):
        state = self._states.get(item_id)
        if state is not None and state.deadline is not None:
            seconds = max(0, state.deadline - elapsed)
            return [Change(False, seconds, real_now + timedelta(seconds=seconds), "real", "latest")], None
        return [], "Rozsvícení závisí na podílu domácností a náhodném výběru"
