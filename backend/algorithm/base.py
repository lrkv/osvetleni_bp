from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Change:
    on: bool
    seconds: float | None
    at: datetime
    basis: str
    kind: str = "scheduled"


class Algorithm(ABC):
    """Common interface for output calculation and read-only event prediction."""
    identifier: str
    time_required = True
    shared = False

    @staticmethod
    @abstractmethod
    def name() -> str:
        """Display name sent to the web UI."""

    @abstractmethod
    def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
        """MTB output: 0 = off, 1 = on, 60 = flashing."""

    def prepare(self, item_ids, now):
        """Update shared state once per calculation, before individual outputs."""

    def reset(self):
        pass

    def forget(self, item_id):
        pass

    def fixed_changes(self, now, sunrise, sunset):
        return []

    def forecast(self, item_id, now, sunrise, sunset, speed, source, real_now, elapsed):
        """Return (known changes, optional reason for an unknown next change)."""
        return [], None


class ScheduledAlgorithm(Algorithm):
    def boundaries(self, date, sunrise, sunset):
        return []

    def fixed_changes(self, now, sunrise, sunset):
        candidates = {at for day in range(-1, 3)
                      for at in self.boundaries((now + timedelta(days=day)).date(), sunrise, sunset)}
        changes = []
        for at in sorted(candidates):
            if now < at <= now + timedelta(days=1):
                before = self.compute(at - timedelta(seconds=1), sunrise, sunset)
                after = self.compute(at, sunrise, sunset)
                if before != after:
                    changes.append((at, bool(after)))
        return changes

    def forecast(self, item_id, now, sunrise, sunset, speed, source, real_now, elapsed):
        if now is None:
            return [], "Čeká na čas hJOP"
        return [Change(on, (at - now).total_seconds() / speed if speed > 0 else None, at, source)
                for at, on in self.fixed_changes(now, sunrise, sunset)], None
