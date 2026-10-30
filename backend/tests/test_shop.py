import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algorithm.shop import Shop
from configurate import load_settings
from service import LightingService
from events import upcoming_events


class ShopTests(unittest.TestCase):
    def test_custom_times_flow_from_settings_to_outputs_and_forecast(self):
        settings = load_settings()
        settings["light"]["shop"] = {"opening_time": "09:15", "closing_time": "17:45"}
        service = LightingService(settings)
        manager = service.manager
        manager.items_by_id.clear()
        manager.tree_data = {"groups": []}
        light = {"name": "Shop", "address": "1:0", "algorithm": "prodejna"}
        manager._process_item(light)
        manager.tree_data["groups"].append(light)
        base = datetime(2026, 10, 30)
        for hour, minute, second, expected in ((9, 14, 59, 0), (9, 15, 0, 1),
                                               (17, 44, 59, 1), (17, 45, 0, 0)):
            now = base.replace(hour=hour, minute=minute, second=second)
            self.assertEqual(manager.calculate_outputs("06:00", "20:00", now=now), {1: {0: expected}})
        now = base.replace(hour=9)
        status = {"source": "hjop", "available": True, "running": True, "speed": 5}
        events = upcoming_events(manager, "06:00", "20:00", now, status, now)["events"]
        self.assertEqual([(row["time"], row["on"]) for row in events], [("09:15:00", True), ("17:45:00", False)])
        self.assertEqual(events[0]["seconds"], 180)

    def test_overnight_interval_and_forecast(self):
        shop = Shop("22:00", "02:00")
        base = datetime(2026, 10, 30)
        for hour, minute, expected in ((21, 59, 0), (22, 0, 1), (23, 59, 1), (0, 0, 1), (1, 59, 1), (2, 0, 0)):
            self.assertEqual(shop.compute(base.replace(hour=hour, minute=minute), "", ""), expected)
        now = base.replace(hour=23)
        self.assertEqual(shop.fixed_changes(now, "", ""),
                         [(base + timedelta(days=1, hours=2), False),
                          (base + timedelta(days=1, hours=22), True)])

    def test_invalid_times_are_rejected_before_startup(self):
        for opening, closing in (("25:00", "19:00"), ("07:60", "19:00"),
                                 ("7:00", "19:00"), (700, "19:00"),
                                 ("07:00", None), ("07:00", "07:00")):
            with self.subTest(opening=opening, closing=closing):
                settings = load_settings()
                settings["light"]["shop"] = {"opening_time": opening, "closing_time": closing}
                with self.assertRaises(ValueError):
                    LightingService(settings)
