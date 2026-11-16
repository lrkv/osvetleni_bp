"""Compatibility imports. Algorithm implementations live in algorithm/."""
from datetime import datetime
from algorithm import ALGORITHMS, ALGORITHM_LABELS, CorridorLighting, HouseholdLighting
from algorithm.household import HouseholdSchedule, household_ratio, _HouseholdState
from algorithm.time_utils import parse_time_to_datetime


def evaluate_algorithm(algorithm_name, sunrise_str="00:00", sunset_str="00:00", *,
                       corridor=None, now=None, household_output=None):
    cls = ALGORITHMS.get(algorithm_name)
    if cls is None:
        return 0
    if cls.shared:
        if household_output is None:
            raise ValueError("Domácnosti musí vyhodnotit společný správce HouseholdLighting.")
        return household_output
    from configurate import ConfigManager, load_settings
    manager = ConfigManager.from_settings(load_settings()["light"])
    instance = corridor if corridor is not None else manager.algorithm_for({"id": 0, "algorithm": algorithm_name})
    return instance.compute(now if now is not None else datetime.now(), sunrise_str, sunset_str)
