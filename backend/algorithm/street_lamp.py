from datetime import timedelta
from .base import ScheduledAlgorithm
from .time_utils import parse_time_to_datetime


class StreetLamp(ScheduledAlgorithm):
    identifier = "poulicni_lampa"

    @staticmethod
    def name() -> str:
        return "Pouliční lampa"

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        off = parse_time_to_datetime(sunrise, now.date()) + timedelta(hours=1)
        on = parse_time_to_datetime(sunset, now.date()) - timedelta(hours=1)
        return int(now >= on or now <= off)

    def boundaries(self, date, sunrise, sunset):
        rise = parse_time_to_datetime(sunrise, date)
        return [rise.replace(hour=0, minute=0), rise + timedelta(hours=1, seconds=1),
                parse_time_to_datetime(sunset, date) - timedelta(hours=1)]
