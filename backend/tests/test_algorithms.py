import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algorithms import evaluate_algorithm, parse_time_to_datetime
from configurate import ConfigManager, SUPPORTED_ALGORITHMS, load_settings


class RailwayLightingTests(unittest.TestCase):
    def evaluate_at(self, instant, sunrise="5:32", sunset="20:09"):
        with patch("algorithms.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime.fromisoformat(instant)
            return evaluate_algorithm("drazni_osvetleni", sunrise, sunset)

    def test_switching_boundaries_and_midnight(self):
        cases = {
            "2026-10-25T20:23:59": 0,
            "2026-10-25T20:24:00": 1,
            "2026-10-25T20:24:01": 1,
            "2026-10-25T23:59:59": 1,
            "2026-10-26T00:00:00": 1,
            "2026-10-26T05:16:59": 1,
            "2026-10-26T05:17:00": 0,
            "2026-10-26T05:17:01": 0,
            "2026-10-26T12:00:00": 0,
        }
        for instant, expected in cases.items():
            with self.subTest(instant=instant):
                self.assertEqual(self.evaluate_at(instant), expected)

    def test_configured_times_change_the_schedule(self):
        self.assertEqual(self.evaluate_at("2026-10-25T18:14:59", "7:00", "18:00"), 0)
        self.assertEqual(self.evaluate_at("2026-10-25T18:15:00", "7:00", "18:00"), 1)
        self.assertEqual(self.evaluate_at("2026-10-26T06:44:59", "7:00", "18:00"), 1)
        self.assertEqual(self.evaluate_at("2026-10-26T06:45:00", "7:00", "18:00"), 0)

    def test_offsets_can_cross_midnight(self):
        cases = [
            ("2026-12-31T23:59:59", "5:32", "23:55", 0),
            ("2027-01-01T00:09:59", "5:32", "23:55", 0),
            ("2027-01-01T00:10:00", "5:32", "23:55", 1),
            ("2027-01-01T05:17:00", "5:32", "23:55", 0),
            ("2026-10-25T23:54:59", "00:10", "20:09", 1),
            ("2026-10-25T23:55:00", "00:10", "20:09", 0),
            ("2026-10-26T00:00:00", "00:10", "20:09", 0),
        ]
        for instant, sunrise, sunset, expected in cases:
            with self.subTest(instant=instant, sunrise=sunrise, sunset=sunset):
                self.assertEqual(self.evaluate_at(instant, sunrise, sunset), expected)

    def test_night_shorter_than_offsets_stays_off(self):
        for instant in ("2026-10-25T23:00:00", "2026-10-26T00:00:00", "2026-10-26T00:10:00"):
            self.assertEqual(self.evaluate_at(instant, "00:10", "23:55"), 0)

    def test_manager_uses_config_times_and_accepts_algorithm(self):
        settings = load_settings()
        sunrise, sunset = str(settings["light"]["sunrise"]), str(settings["light"]["sunset"])
        manager = ConfigManager()
        item = {"id": 1, "name": "Peron 1", "address": "1:2", "algorithm": "trvale_vypnuto"}
        manager.items_by_id = {1: item}
        self.assertIn("drazni_osvetleni", SUPPORTED_ALGORITHMS)
        self.assertTrue(manager.change_algorithm(1, "drazni_osvetleni"))
        today = datetime(2026, 10, 25)
        on = parse_time_to_datetime(sunset, today) + timedelta(minutes=15)
        off = parse_time_to_datetime(sunrise, today) - timedelta(minutes=15)
        for instant, expected in ((on, 1), (off, 0)):
            with patch("algorithms.datetime", wraps=datetime) as clock:
                clock.now.return_value = instant
                self.assertEqual(manager.calculate_outputs(sunrise, sunset)[1][2], expected)
                self.assertEqual(item["is_on"], bool(expected))
                self.assertNotIn("configuration_error", item)


if __name__ == "__main__":
    unittest.main()
