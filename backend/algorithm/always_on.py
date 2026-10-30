from .base import Algorithm


class AlwaysOn(Algorithm):
    identifier = "trvale_zapnuto"
    time_required = False

    @staticmethod
    def name() -> str:
        return "zapnuto"

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        return 1
