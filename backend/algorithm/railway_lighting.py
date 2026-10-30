from datetime import timedelta
from .base import ScheduledAlgorithm
from .time_utils import parse_time_to_datetime


class RailwayLighting(ScheduledAlgorithm):
    identifier = "drazni_osvetleni"

    @staticmethod
    def name() -> str:
        return "Drážní osvětlení"

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        setting = parse_time_to_datetime(sunset, now.date())
        rise = parse_time_to_datetime(sunrise, now.date())
        if rise <= setting:
            rise += timedelta(days=1)
        on = setting + timedelta(minutes=15)
        off = rise - timedelta(minutes=15)
        return int(any(on - timedelta(days=day) <= now < off - timedelta(days=day)
                       for day in (0, 1)))

    def boundaries(self, date, sunrise, sunset):
        return [parse_time_to_datetime(sunrise, date) - timedelta(minutes=15),
                parse_time_to_datetime(sunset, date) + timedelta(minutes=15)]
