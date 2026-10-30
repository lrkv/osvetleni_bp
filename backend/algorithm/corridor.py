import random
import math
from datetime import timedelta
from time import monotonic
from .base import Algorithm, Change
from .time_utils import parse_time_to_datetime


class CorridorLighting(Algorithm):
    """One independent schedule per light; deadlines use a monotonic clock."""
    identifier = "chodba"

    @staticmethod
    def name() -> str:
        return "Chodba"

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

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        return self.evaluate(now, sunrise, sunset)

    def forecast(self, item_id, now, sunrise, sunset, speed, source, real_now, elapsed):
        if self.deadline is None or now is None:
            return [], "Další rozsvícení se losuje během noci"
        seconds = max(0, self.deadline - elapsed)
        dawn = parse_time_to_datetime(sunrise, now.date())
        if dawn <= now:
            dawn += timedelta(days=1)
        until_dawn = (dawn - now).total_seconds() / speed if speed > 0 else math.inf
        if until_dawn <= seconds:
            if self.is_on:
                return [Change(False, until_dawn, dawn, source)], None
            return [], "Pauza končí až po východu slunce"
        return [Change(not self.is_on, seconds, real_now + timedelta(seconds=seconds), "real")], None
