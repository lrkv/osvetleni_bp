from .base import Algorithm


class AlwaysOff(Algorithm):
    identifier = "trvale_vypnuto"
    time_required = False

    @staticmethod
    def name() -> str:
        return "vypnuto"

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        return 0
