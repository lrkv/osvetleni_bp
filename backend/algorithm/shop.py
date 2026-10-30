import re
from datetime import datetime, time
from .base import ScheduledAlgorithm


class Shop(ScheduledAlgorithm):
    identifier = "prodejna"

    @staticmethod
    def name() -> str:
        return "Prodejna"

    def __init__(self, opening_time="07:00", closing_time="19:00"):
        self.opening_time = self._parse_time(opening_time, "opening_time")
        self.closing_time = self._parse_time(closing_time, "closing_time")
        if self.opening_time == self.closing_time:
            raise ValueError("shop.opening_time a shop.closing_time musí být různé.")

    @staticmethod
    def _parse_time(value, key):
        if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value, flags=re.ASCII):
            raise ValueError(f"shop.{key} musí být čas ve formátu HH:MM (00:00–23:59).")
        return time.fromisoformat(value)

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        current = now.time()
        if self.opening_time < self.closing_time:
            return int(self.opening_time <= current < self.closing_time)
        return int(current >= self.opening_time or current < self.closing_time)

    def boundaries(self, date, sunrise, sunset):
        return [datetime.combine(date, value) for value in (self.opening_time, self.closing_time)]
