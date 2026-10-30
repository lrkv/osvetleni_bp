import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algorithms import CorridorLighting, evaluate_algorithm
from configurate import ConfigManager, SUPPORTED_ALGORITHMS, load_settings
from service import LightingService


class BuildingAlgorithmsTests(unittest.TestCase):
    def at(self, algorithm, time, sunrise="5:32", sunset="20:09"):
        with patch("algorithms.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime.fromisoformat("2026-10-25T" + time)
            return evaluate_algorithm(algorithm, sunrise, sunset)

    def test_prodejna_boundaries(self):
        for time, expected in (("06:59:59", 0), ("07:00:00", 1),
                               ("18:59:59", 1), ("19:00:00", 0),
                               ("00:00:00", 0), ("23:59:59", 0)):
            with self.subTest(time=time):
                self.assertEqual(self.at("prodejna", time), expected)

    def test_vyloha_is_always_on(self):
        for time in ("00:00:00", "05:32:00", "12:00:00", "20:09:00", "23:59:59"):
            self.assertEqual(self.at("vyloha", time), 1)

    def test_all_new_modes_are_accepted_and_published(self):
        settings = load_settings()
        settings["configurate"] = "lrkv_tt.yaml"
        service = LightingService(settings)
        for mode in ("domacnost", "chodba", "prodejna", "vyloha"):
            self.assertIn(mode, SUPPORTED_ALGORITHMS)
            item = next(x for x in service.manager.items_by_id.values() if "address" in x)
            self.assertTrue(service.manager.change_algorithm(item["id"], mode))
        service.recalculate()
        self.assertIn('"chodba"', service.snapshot)


class CorridorTests(unittest.TestCase):
    def evaluate(self, state, elapsed, instant="2026-10-25T22:00:00"):
        with patch("algorithms.monotonic", return_value=elapsed):
            return state.evaluate(datetime.fromisoformat(instant), "5:32", "20:09")

    def test_random_intervals_are_stable_between_recalculations(self):
        state = CorridorLighting()
        with patch("algorithms.random.randint", side_effect=[60, 20, 300, 30, 60]) as rng:
            self.assertEqual(self.evaluate(state, 0), 0)
            self.assertEqual(self.evaluate(state, 59.99), 0)
            self.assertEqual(rng.call_count, 1)
            self.assertEqual(self.evaluate(state, 60), 1)
            self.assertEqual(self.evaluate(state, 79.99), 1)
            self.assertEqual(self.evaluate(state, 80), 0)
            self.assertEqual(self.evaluate(state, 379.99), 0)
            self.assertEqual(self.evaluate(state, 380), 1)
            self.assertEqual(self.evaluate(state, 409.99), 1)
            self.assertEqual(self.evaluate(state, 410), 0)
            self.assertEqual([call.args for call in rng.call_args_list],
                             [(60, 300), (20, 30), (60, 300), (20, 30), (60, 300)])

    def test_dawn_cuts_off_light_and_new_night_starts_new_schedule(self):
        state = CorridorLighting()
        with patch("algorithms.random.randint", side_effect=[60, 30, 120]) as rng:
            self.assertEqual(self.evaluate(state, 0), 0)
            self.assertEqual(self.evaluate(state, 60, "2026-10-26T05:31:59"), 1)
            self.assertEqual(self.evaluate(state, 61, "2026-10-26T05:32:00"), 0)
            self.assertIsNone(state.deadline)
            self.assertEqual(self.evaluate(state, 100, "2026-10-26T12:00:00"), 0)
            self.assertEqual(rng.call_count, 2)
            self.assertEqual(self.evaluate(state, 200, "2026-10-26T20:09:00"), 0)
            self.assertEqual(state.deadline, 320)

    def test_midnight_does_not_reset_light(self):
        state = CorridorLighting()
        with patch("algorithms.random.randint", side_effect=[60, 30]) as rng:
            self.evaluate(state, 0, "2026-10-25T23:58:55")
            self.assertEqual(self.evaluate(state, 60, "2026-10-25T23:59:55"), 1)
            self.assertEqual(self.evaluate(state, 65, "2026-10-26T00:00:00"), 1)
            self.assertEqual(rng.call_count, 2)

    def test_daytime_never_draws_random_numbers(self):
        with patch("algorithms.random.randint") as rng:
            self.assertEqual(self.evaluate(CorridorLighting(), 0, "2026-10-25T12:00:00"), 0)
            self.assertEqual(self.evaluate(CorridorLighting(), 0, "2026-10-25T20:08:59"), 0)
            rng.assert_not_called()

    def test_each_light_is_independent_and_mode_changes_reset_state(self):
        manager = ConfigManager()
        manager.items_by_id = {
            1: {"id": 1, "name": "A", "address": "1:0", "algorithm": "chodba"},
            2: {"id": 2, "name": "B", "address": "1:1", "algorithm": "chodba"},
        }
        with patch("algorithms.datetime", wraps=datetime) as clock, \
             patch("algorithms.monotonic", return_value=0) as elapsed, \
             patch("algorithms.random.randint", side_effect=[60, 120, 20, 180]):
            clock.now.return_value = datetime(2026, 10, 25, 22)
            self.assertEqual(manager.calculate_outputs("5:32", "20:09"), {1: {0: 0, 1: 0}})
            elapsed.return_value = 60
            self.assertEqual(manager.calculate_outputs("5:32", "20:09"), {1: {0: 1, 1: 0}})
            first_state = manager._corridors[1]
            manager.change_algorithm(1, "chodba")
            manager.calculate_outputs("5:32", "20:09")
            self.assertIs(manager._corridors[1], first_state)
            manager.change_algorithm(1, "prodejna")
            self.assertNotIn(1, manager._corridors)
            manager.change_algorithm(1, "chodba")
            manager.calculate_outputs("5:32", "20:09")
            self.assertIsNot(manager._corridors[1], first_state)
            self.assertEqual(manager._corridors[1].deadline, 240)
            self.assertEqual(manager._corridors[2].deadline, 120)

    def test_pause_range_is_configurable_and_validated(self):
        settings = load_settings()
        settings["light"]["corridor"] = {"pause_min_seconds": 90, "pause_max_seconds": 180}
        service = LightingService(settings)
        self.assertEqual(service.manager.corridor_pause_min, 90)
        self.assertEqual(service.manager.corridor_pause_max, 180)
        for limits in ((0, 10), (60, 30), (-1, 30)):
            with self.assertRaises(ValueError):
                ConfigManager(*limits)


if __name__ == "__main__":
    unittest.main()
