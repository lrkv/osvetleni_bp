from .base import Algorithm


class ShopWindow(Algorithm):
    identifier = "vyloha"
    time_required = False

    @staticmethod
    def name() -> str:
        return "Výloha"

    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        return 1
