from .base import Algorithm


class Disco(Algorithm):
    identifier = "disco"
    time_required = False

    @staticmethod
    def name() -> str:
        return "Blikání (disco)"

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        return 60
