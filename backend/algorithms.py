import random
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import monotonic

# Vlevo je identifikátor v YAML/API, vpravo název zobrazovaný na webu.
ALGORITHM_LABELS = {
    "trvale_zapnuto": "zapnuto",
    "trvale_vypnuto": "vypnuto",
    "domacnost": "Domácnost",
    "poulicni_lampa": "Pouliční lampa",
    "drazni_osvetleni": "Drážní osvětlení",
    "chodba": "Chodba",
    "prodejna": "Prodejna",
    "vyloha": "Výloha",
    "disco": "Blikání (disco)",
    "minuta": "Minuta",
}


def parse_time_to_datetime(time_str: str, current_date: datetime.date) -> datetime:
    """
    Pomocná funkce, která vezme text (např. '5:32') a dnešní datum,
    a vytvoří z nich plnohodnotný časový údaj pro matematické operace.
    """
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])

    return datetime(
        year=current_date.year,
        month=current_date.month,
        day=current_date.day,
        hour=hours,
        minute=minutes
    )


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


class HouseholdLighting:
    """One coordinator for every household light, with real-time dwell limits."""
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

    def reset(self):
        self._states.clear()

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


class CorridorLighting:
    """One independent schedule per light; deadlines use a monotonic clock."""
    def __init__(self, pause_min_seconds=60, pause_max_seconds=300, min_on_seconds=20, max_on_seconds=30):
        values = (pause_min_seconds, pause_max_seconds, min_on_seconds, max_on_seconds)
        if (any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values)
                or pause_min_seconds > pause_max_seconds or min_on_seconds > max_on_seconds):
            raise ValueError("Intervaly corridor musí být kladná celá čísla; minimum nesmí překročit maximum.")
        self.min_on_seconds = min_on_seconds
        self.max_on_seconds = max_on_seconds
        self.pause_min_seconds = pause_min_seconds
        self.pause_max_seconds = pause_max_seconds
        self.night_start = None
        self.is_on = False
        self.deadline = None

    def evaluate(self, now, sunrise_str, sunset_str):
        sunset = parse_time_to_datetime(sunset_str, now.date())
        sunrise = parse_time_to_datetime(sunrise_str, now.date())
        if sunrise <= sunset:
            sunrise += timedelta(days=1)
        night_start = None
        for days_ago in (0, 1):
            shift = timedelta(days=days_ago)
            if sunset - shift <= now < sunrise - shift:
                night_start = sunset - shift
                break

        if night_start is None:
            self.night_start = None
            self.is_on = False
            self.deadline = None
            return 0

        elapsed = monotonic()
        if self.night_start != night_start:
            self.night_start = night_start
            self.is_on = False
            self.deadline = elapsed + random.randint(self.pause_min_seconds, self.pause_max_seconds)
        elif elapsed >= self.deadline:
            self.is_on = not self.is_on
            duration = (random.randint(self.min_on_seconds, self.max_on_seconds) if self.is_on else
                        random.randint(self.pause_min_seconds, self.pause_max_seconds))
            self.deadline = elapsed + duration
        return int(self.is_on)


def evaluate_algorithm(algorithm_name: str, sunrise_str: str = "00:00", sunset_str: str = "00:00", *, corridor: CorridorLighting | None = None, now: datetime | None = None, household_output: int | None = None) -> int:
    """
    Vyhodnotí algoritmus a vrátí hodnotu pro MTB démona:
    1 = zapnuto
    0 = vypnuto
    60 = blikání (kmitání)
    """

    # --- 1. Statické stavy ---
    if algorithm_name in ("trvale_zapnuto", "vyloha"):
        return 1

    elif algorithm_name == "trvale_vypnuto":
        return 0

    elif algorithm_name == "disco":
        return 60

    elif algorithm_name == "chodba":
        if corridor is None:
            raise ValueError("Algoritmus chodba potřebuje vlastní instanci CorridorLighting.")
        return corridor.evaluate(now if now is not None else datetime.now(), sunrise_str, sunset_str)

    elif algorithm_name == "minuta":
        now = now if now is not None else datetime.now()
        return now.minute % 2

    elif algorithm_name == "prodejna":
        now = now if now is not None else datetime.now()
        return int(7 <= now.hour < 19)

    # --- 2. Dynamické časové stavy ---
    elif algorithm_name == "poulicni_lampa":
        now = now if now is not None else datetime.now()
        today = now.date()

        sunrise_dt = parse_time_to_datetime(sunrise_str, today)
        sunset_dt = parse_time_to_datetime(sunset_str, today)

        lights_off_time = sunrise_dt + timedelta(hours=1)
        lights_on_time = sunset_dt - timedelta(hours=1)

        if now >= lights_on_time or now <= lights_off_time:
            return 1
        else:
            return 0

    elif algorithm_name == "domacnost":
        if household_output is None:
            raise ValueError("Domácnosti musí vyhodnotit společný správce HouseholdLighting.")
        return household_output

    elif algorithm_name == "drazni_osvetleni":
        now = now if now is not None else datetime.now()
        sunset_dt = parse_time_to_datetime(sunset_str, now.date())
        sunrise_dt = parse_time_to_datetime(sunrise_str, now.date())
        if sunrise_dt <= sunset_dt:
            sunrise_dt += timedelta(days=1)

        lights_on_time = sunset_dt + timedelta(minutes=15)
        lights_off_time = sunrise_dt - timedelta(minutes=15)
        # Check the nights starting today and yesterday. Offsets may cross midnight.
        for days_ago in (0, 1):
            shift = timedelta(days=days_ago)
            if lights_on_time - shift <= now < lights_off_time - shift:
                return 1
        return 0

    # Výchozí ochrana pro neznámé algoritmy
    else:
        print(f"Algoritmus: {algorithm_name} není implementovaný.")
    return 0