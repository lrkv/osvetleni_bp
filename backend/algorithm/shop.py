from datetime import datetime, time
from .base import ScheduledAlgorithm


class Shop(ScheduledAlgorithm):
    identifier = "prodejna"

    @staticmethod
    def name() -> str:
        return "Prodejna"

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        return int(7 <= now.hour < 19)

    def boundaries(self, date, sunrise, sunset):
        return [datetime.combine(date, time(hour)) for hour in (7, 19)]
