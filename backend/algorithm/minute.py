from datetime import timedelta
from .base import ScheduledAlgorithm


class Minute(ScheduledAlgorithm):
    identifier = "minuta"

    @staticmethod
    def name() -> str:
        return "Minuta"

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        return now.minute % 2

    def fixed_changes(self, now, sunrise, sunset):
        first = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        return [(at, bool(self.compute(at, sunrise, sunset)))
                for at in (first, first + timedelta(minutes=1))]
