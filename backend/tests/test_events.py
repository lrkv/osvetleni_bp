import sys
import random
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config_fixtures import make_manager, make_corridor
from algorithms import _HouseholdState
from configurate import load_settings
from events import upcoming_events, fixed_changes
from service import LightingService

NOW = datetime(2026, 10, 29, 18, 59)
STATUS = {"source": "hjop", "running": True, "available": True, "speed": 10}

class EventTests(unittest.TestCase):
    def manager(self, algorithms):
        manager = make_manager()
        manager.tree_data = {"groups": [{"name": str(i), "address": f"1:{i}", "algorithm": algorithm}
                                       for i, algorithm in enumerate(algorithms)]}
        for node in manager.tree_data["groups"]:
            manager._process_item(node)
        return manager

    def test_fixed_boundaries_include_next_day(self):
        changes = fixed_changes("prodejna", NOW, "6:00", "20:00")
        self.assertEqual(changes, [(NOW.replace(hour=19, minute=0), False),
                                  ((NOW + timedelta(days=1)).replace(hour=7, minute=0), True)])
        changes = fixed_changes("drazni_osvetleni", NOW, "6:00", "20:00")
        self.assertEqual([(at.strftime("%H:%M:%S"), on) for at, on in changes],
                         [("20:15:00", True), ("05:45:00", False)])
        street = fixed_changes("poulicni_lampa", NOW, "6:00", "20:00")
        self.assertEqual(street[1][0].strftime("%H:%M:%S"), "07:00:01")

    def test_real_and_model_events_sort_without_mutating_schedules_or_rng(self):
        manager = self.manager(["prodejna", "chodba", "domacnost", "domacnost", "vyloha"])
        corridor = make_corridor()
        corridor.deadline = 110
        manager._instances[2] = corridor
        manager._households._states[3] = _HouseholdState(on_since=90, deadline=120)
        rng = random.getstate()
        with patch("events.monotonic", return_value=100):
            forecast = upcoming_events(manager, "6:00", "20:00", NOW, STATUS, NOW)
        self.assertEqual([row["id"] for row in forecast["events"][:3]], [1, 2, 3])
        self.assertEqual([row["seconds"] for row in forecast["events"][:3]], [6, 10, 20])
        self.assertEqual(forecast["events"][2]["kind"], "latest")
        self.assertEqual(forecast["unknown"][0]["id"], 4)
        self.assertEqual(random.getstate(), rng)
        self.assertEqual(corridor.deadline, 110)
        self.assertFalse(corridor.is_on)

    def test_paused_model_clock_keeps_real_timers(self):
        manager = self.manager(["prodejna", "domacnost"])
        manager._households._states[2] = _HouseholdState(on_since=90, deadline=120)
        with patch("events.monotonic", return_value=100):
            forecast = upcoming_events(manager, "6:00", "20:00", NOW, {**STATUS, "running": False}, NOW)
        self.assertTrue(forecast["model_paused"])
        self.assertEqual(forecast["events"][0]["seconds"], 20)
        self.assertIsNone(forecast["events"][1]["seconds"])

    def test_dawn_cancels_corridor_turn_on(self):
        manager = self.manager(["chodba"])
        corridor = make_corridor()
        corridor.deadline = 130
        manager._instances[1] = corridor
        now = NOW.replace(hour=5, minute=59)
        with patch("events.monotonic", return_value=100):
            forecast = upcoming_events(manager, "6:00", "20:00", now, STATUS, NOW)
            self.assertEqual(forecast["events"], [])
            corridor.is_on = True
            forecast = upcoming_events(manager, "6:00", "20:00", now, STATUS, NOW)
            self.assertEqual(forecast["events"][0]["seconds"], 6)
            self.assertFalse(forecast["events"][0]["on"])

    def test_missing_clock_and_static_algorithms(self):
        manager = self.manager(["prodejna", "vyloha", "trvale_zapnuto"])
        forecast = upcoming_events(manager, "6:00", "20:00", None, {**STATUS, "available": False}, NOW)
        self.assertEqual(forecast["events"], [])
        self.assertEqual(len(forecast["unknown"]), 1)

    def test_initial_subscription_contains_events_and_changes_have_separate_message(self):
        import json
        settings = load_settings()
        settings["hjop"]["enabled"] = False
        service = LightingService(settings)
        service.recalculate()
        queue = service.subscribe()
        self.assertIn("upcoming", json.loads(queue.get_nowait()))
        service.events_snapshot = ""
        service.publish_events(NOW)
        self.assertEqual(json.loads(queue.get_nowait())["type"], "events")

    def test_minute_algorithm_boundaries_and_midnight(self):
        from algorithms import evaluate_algorithm
        for time, expected in (("23:59:59", 1), ("00:00:00", 0), ("00:01:00", 1), ("00:02:00", 0)):
            now = datetime.fromisoformat("2026-10-30T" + time)
            self.assertEqual(evaluate_algorithm("minuta", now=now), expected)
        now = NOW.replace(hour=23, minute=59, second=50)
        changes = fixed_changes("minuta", now, "6:00", "20:00")
        self.assertEqual([(at.strftime("%H:%M:%S"), on) for at, on in changes], [("00:00:00", False), ("00:01:00", True)])
        self.assertEqual(changes[0][0].date(), (now + timedelta(days=1)).date())

    def test_real_timer_projects_hjop_time_and_paused_clock_does_not_guess(self):
        manager = self.manager(["chodba", "minuta", "minuta"])
        corridor = make_corridor()
        corridor.deadline = 110
        manager._instances[1] = corridor
        with patch("events.monotonic", return_value=100):
            forecast = upcoming_events(manager, "6:00", "20:00", NOW, STATUS, NOW)
            corridor_row = next(row for row in forecast["events"] if row["id"] == 1)
            self.assertEqual(corridor_row["model_time"], "19:00:40")
            minute_rows = [row for row in forecast["events"] if row["algorithm"] == "minuta"]
            self.assertEqual(minute_rows[0]["at_key"], minute_rows[1]["at_key"])
            self.assertEqual(minute_rows[0]["model_time"], "19:00:00")
            paused = upcoming_events(manager, "6:00", "20:00", NOW, {**STATUS, "running": False}, NOW)
            self.assertIsNone(next(row for row in paused["events"] if row["id"] == 1)["model_time"])
