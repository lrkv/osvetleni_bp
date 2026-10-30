import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algorithm import Algorithm, ALGORITHMS, ALGORITHM_LABELS
from configurate import ConfigManager


class AlgorithmClassTests(unittest.TestCase):
    def test_registry_has_concrete_classes_and_web_names(self):
        with self.assertRaises(TypeError):
            Algorithm()
        self.assertEqual(len({cls.__module__ for cls in ALGORITHMS.values()}), len(ALGORITHMS))
        for identifier, cls in ALGORITHMS.items():
            with self.subTest(identifier=identifier):
                instance = cls()
                self.assertIsInstance(instance, Algorithm)
                self.assertEqual(instance.identifier, identifier)
                self.assertEqual(ALGORITHM_LABELS[identifier], instance.name())
                self.assertIsInstance(instance.name(), str)
                self.assertNotIn("_", instance.name())

    def test_manager_dispatches_a_new_class_without_algorithm_specific_branches(self):
        class TestAlgorithm(Algorithm):
            identifier = "test"

            @staticmethod
            def name() -> str:
                return "Test"

            def compute(self, now, sunrise, sunset, *, item_id=None) -> int:
                return int(now.hour == 12 and item_id == 1)

        manager = ConfigManager()
        manager._factories[TestAlgorithm.identifier] = TestAlgorithm
        manager._process_item({"name": "Test", "address": "1:0", "algorithm": "test"})
        self.assertEqual(manager.calculate_outputs("06:00", "20:00", now=datetime(2026, 1, 1, 12)), {1: {0: 1}})
        self.assertEqual(manager.calculate_outputs("06:00", "20:00", now=datetime(2026, 1, 1, 13)), {1: {0: 0}})

    def test_corridors_have_separate_instances_and_households_share_coordinator(self):
        manager = ConfigManager()
        for index, identifier in enumerate(("chodba", "chodba", "domacnost", "domacnost")):
            manager._process_item({"name": str(index), "address": f"1:{index}", "algorithm": identifier})
        instances = [manager.algorithm_for(item) for item in manager.items_by_id.values()]
        self.assertIsNot(instances[0], instances[1])
        self.assertIs(instances[2], instances[3])
