import json
import random
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algorithms import ALGORITHM_LABELS, HouseholdLighting, HouseholdSchedule, household_ratio
from configurate import BASE_DIR, ConfigManager, SUPPORTED_ALGORITHMS, load_settings
from service import LightingService


def instant(time):
    return datetime.fromisoformat("2026-10-26T" + time)


def evaluate(controller, elapsed, time="19:00:00", members=range(10)):
    with patch("algorithms.monotonic", return_value=elapsed):
        return controller.evaluate(members, instant(time) if time else None)


class HouseholdTests(unittest.TestCase):
    def test_schedule_boundaries_and_linear_transitions(self):
        cases = {
            "00:00:00": .10, "03:59:59": .10, "04:00:00": .10,
            "04:15:00": .20, "04:30:00": .30, "04:45:00": .40,
            "04:59:59": .50 - .40 / 3600, "05:00:00": .70,
            "05:59:59": .70, "06:00:00": .50, "07:59:59": .50,
            "08:00:00": .05, "18:59:59": .05, "19:00:00": .70,
            "20:59:59": .70, "21:00:00": .70, "21:30:00": .625,
            "22:00:00": .55, "22:30:00": .475,
            "22:59:59": .40 + .15 / 3600, "23:00:00": .10, "23:59:59": .10,
        }
        for time, ratio in cases.items():
            with self.subTest(time=time):
                self.assertAlmostEqual(household_ratio(instant(time)), ratio)

    def test_target_counts_and_nearest_integer_rounding(self):
        for time, expected in (("19:00:00", 14), ("22:00:00", 11), ("23:00:00", 2),
                               ("04:30:00", 6), ("05:00:00", 14), ("06:00:00", 10),
                               ("08:00:00", 1)):
            with self.subTest(time=time):
                self.assertEqual(sum(evaluate(HouseholdLighting(), 0, time, range(20)).values()), expected)
        self.assertEqual(sum(evaluate(HouseholdLighting(), 0, "12:00:00", range(13)).values()), 1)
        self.assertEqual(sum(evaluate(HouseholdLighting(), 0, "12:00:00", range(3)).values()), 0)
        self.assertEqual(evaluate(HouseholdLighting(), 0, members=[]), {})

    def test_minimum_survives_model_time_jump_and_maximum_uses_real_time(self):
        controller = HouseholdLighting()
        with patch("algorithms.random.uniform", return_value=300):
            initial = evaluate(controller, 0)
            self.assertEqual(sum(initial.values()), 7)
            # Model time jumps into daytime; real on-period is still shorter than 30 s.
            self.assertEqual(evaluate(controller, 29, "12:00:00"), initial)
            reduced = evaluate(controller, 30, "12:00:00")
            self.assertEqual(sum(reduced.values()), 1)
            survivor = next(key for key, value in reduced.items() if value)
            self.assertEqual(evaluate(controller, 299, "12:00:00")[survivor], 1)
            self.assertEqual(evaluate(controller, 300, "12:00:00")[survivor], 0)
            self.assertEqual(evaluate(controller, 329, "12:00:00")[survivor], 0)

    def test_rotation_and_minimum_off_time_even_with_paused_model_clock(self):
        controller = HouseholdLighting(30, 30, 30)
        first = evaluate(controller, 0)
        self.assertEqual(evaluate(controller, 29), first)
        second = evaluate(controller, 30)
        # At 70 % with equal 30 s on/off, all 7 expired lights must really turn off.
        self.assertEqual(sum(second.values()), 3)
        self.assertTrue(all(not second[key] for key, value in first.items() if value))
        self.assertEqual(evaluate(controller, 59), second)
        third = evaluate(controller, 60)
        self.assertEqual(sum(third.values()), 7)
        self.assertTrue(all(not third[key] for key, value in second.items() if value))

    def test_random_duration_is_drawn_once_per_on_period(self):
        controller = HouseholdLighting(45, 90, 30)
        with patch("algorithms.random.uniform", return_value=60) as rng:
            first = evaluate(controller, 0)
            self.assertEqual(rng.call_count, 7)
            for elapsed in (0, 1, 20, 44, 59):
                self.assertEqual(evaluate(controller, elapsed), first)
            self.assertEqual(rng.call_count, 7)
            self.assertTrue(all(call.args == (45, 90) for call in rng.call_args_list))
            next_state = evaluate(controller, 60)
            self.assertTrue(all(not next_state[key] for key, value in first.items() if value))

    def test_no_clock_and_membership_changes(self):
        controller = HouseholdLighting()
        self.assertEqual(sum(evaluate(controller, 0, time=None).values()), 0)
        with patch("algorithms.random.uniform", return_value=300):
            first = evaluate(controller, 1)
            on_id = next(key for key, value in first.items() if value)
            changed = evaluate(controller, 2, members=[key for key in range(10) if key != on_id])
            self.assertNotIn(on_id, changed)
            self.assertEqual(len(changed), 9)
            self.assertEqual(sum(changed.values()), 6)
            self.assertEqual(evaluate(controller, 3, members=[]), {})
            controller.reset()
            self.assertEqual(sum(evaluate(controller, 4).values()), 7)

    def test_invalid_limits_fail_early(self):
        for limits in ((0, 300, 30), (301, 300, 30), (30, 300, 0),
                       (30, float("inf"), 30), (float("nan"), 300, 30), ("bad", 300, 30)):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                HouseholdLighting(*limits)

    def test_simulated_run_respects_every_real_on_and_off_interval(self):
        controller = HouseholdLighting()
        rng = random.Random(126)
        last = dict.fromkeys(range(20), 0)
        changed_at = dict.fromkeys(range(20), -1000)
        seen_on = set()
        with patch("algorithms.random.uniform", side_effect=rng.uniform), \
             patch("algorithms.random.shuffle", side_effect=rng.shuffle):
            for elapsed in range(1801):
                state = evaluate(controller, elapsed, members=range(20))
                for key, value in state.items():
                    if value != last[key]:
                        duration = elapsed - changed_at[key]
                        if last[key]:
                            self.assertGreaterEqual(duration, 30)
                            self.assertLessEqual(duration, 301)  # One-second service tick.
                        else:
                            self.assertGreaterEqual(duration, 30)
                            seen_on.add(key)
                        changed_at[key] = elapsed
                    elif value:
                        self.assertLessEqual(elapsed - changed_at[key], 300)
                self.assertLessEqual(sum(state.values()), 14)
                last = state
        self.assertEqual(seen_on, set(range(20)))


class HouseholdIntegrationTests(unittest.TestCase):
    def test_all_groups_and_modules_share_one_target_and_publish_state(self):
        settings = load_settings()
        settings["configurate"] = "lrkv_tt.yaml"
        settings["light"]["household"] = {"min_on_seconds": 45, "max_on_seconds": 90, "min_off_seconds": 35}
        service = LightingService(settings)
        manager = service.manager
        # Four independent groups, ten modules: percentage must be global.
        manager.items_by_id.clear()
        manager.tree_data = {"groups": []}
        for group_id in range(4):
            group = {"name": str(group_id), "items": []}
            for offset in range(5):
                index = group_id * 5 + offset
                group["items"].append({"name": str(index), "address": f"{index // 2 + 1}:{index % 2}", "algorithm": "domacnost"})
            manager._process_item(group)
            manager.tree_data["groups"].append(group)
        self.assertEqual(manager._households.min_on_seconds, 45)
        self.assertEqual(manager._households.max_on_seconds, 90)
        self.assertEqual(manager._households.min_off_seconds, 35)
        with patch("service.datetime") as system_time, patch("algorithms.monotonic", return_value=0):
            system_time.now.return_value = instant("12:00:00")
            service.recalculate()
        self.assertEqual(sum(sum(ports.values()) for ports in service.daemon.desired.values()), 1)
        service.model_clock.connected = True
        with patch("algorithms.monotonic", return_value=0), patch("hjop.monotonic", return_value=0):
            service.model_clock.apply_time("-;MOD-CAS;0;9;19:00:00;1".split(";"))
            self.assertEqual(sum(sum(ports.values()) for ports in service.daemon.desired.values()), 14)
        snapshot = json.loads(service.snapshot)
        self.assertEqual(sum(item["is_on"] for group in snapshot["structure"]["groups"] for item in group["items"]), 14)
        self.assertNotIn("byt", snapshot["algorithms"])
        self.assertEqual(snapshot["algorithm_labels"]["domacnost"], "Domácnost")

    def test_reselect_keeps_state_but_manual_mode_change_resets_it(self):
        manager = ConfigManager()
        for index in range(10):
            manager._process_item({"name": str(index), "address": f"1:{index}", "algorithm": "domacnost"})
        with patch("algorithms.monotonic", return_value=0), patch("algorithms.random.uniform", return_value=300):
            manager.calculate_outputs("5:32", "20:09", now=instant("19:00:00"))
            light = next(item for item in manager.items_by_id.values() if item["is_on"])
            previous = manager._households._states[light["id"]]
            manager.change_algorithm(light["id"], "domacnost")
            manager.calculate_outputs("5:32", "20:09", now=instant("19:00:00"))
            self.assertIs(manager._households._states[light["id"]], previous)
            manager.change_algorithm(light["id"], "trvale_vypnuto")
            manager.calculate_outputs("5:32", "20:09", now=instant("19:00:00"))
            self.assertNotIn(light["id"], manager._households._states)
            self.assertFalse(light["is_on"])
        with self.assertRaises(ValueError):
            manager.change_algorithm(light["id"], "byt")

    def test_all_layouts_use_supported_algorithms_without_byt(self):
        self.assertNotIn("byt", SUPPORTED_ALGORITHMS)
        self.assertNotIn("byt", ALGORITHM_LABELS)
        def visit(nodes):
            for node in nodes:
                if "address" in node:
                    self.assertIn(node["algorithm"], SUPPORTED_ALGORITHMS)
                visit(node.get("items", []))
        for path in (BASE_DIR / "configurate").glob("*.yaml"):
            with self.subTest(path=path.name):
                visit(yaml.safe_load(path.read_text(encoding="utf-8")).get("groups", []))


class ConfigurableScheduleTests(unittest.TestCase):
    def test_constant_intervals_unsorted_input_and_midnight(self):
        schedule = HouseholdSchedule([
            {"time": "19:00", "percent": 80},
            {"time": "07:00", "percent": 20},
        ])
        for time, expected in (("00:00:00", .8), ("06:59:59", .8), ("07:00:00", .2),
                               ("18:59:59", .2), ("19:00:00", .8), ("23:59:59", .8)):
            self.assertAlmostEqual(schedule.ratio(instant(time)), expected)

    def test_linear_interval_across_midnight_and_single_entry(self):
        schedule = HouseholdSchedule([
            {"time": "22:00", "percent": 80, "end_percent": 20},
            {"time": "02:00", "percent": 0},
        ])
        self.assertAlmostEqual(schedule.ratio(instant("22:00:00")), .8)
        self.assertAlmostEqual(schedule.ratio(instant("00:00:00")), .5)
        self.assertAlmostEqual(schedule.ratio(instant("01:00:00")), .35)
        self.assertEqual(schedule.ratio(instant("02:00:00")), 0)
        constant = HouseholdSchedule([{"time": "12:00", "percent": 33.5}])
        for time in ("00:00:00", "12:00:00", "23:59:59"):
            self.assertEqual(constant.ratio(instant(time)), .335)

    def test_bad_configuration_is_rejected(self):
        for entries in ([], {}, [{"time": "24:00", "percent": 10}],
                        [{"time": 400, "percent": 10}], [{"time": "04:60", "percent": 10}],
                        [{"time": "4:0", "percent": 10}], [{"time": "04:00"}],
                        [{"time": "04:00", "percent": -1}], [{"time": "04:00", "percent": 101}],
                        [{"time": "04:00", "percent": True}], [{"time": "04:00", "percent": float("nan")}],
                        [{"time": "04:00", "percent": 10, "end_percent": float("inf")}],
                        [{"time": "04:00", "percent": 10, "end_percnt": 40}],
                        [{"time": "04:00", "percent": 10}, {"time": "4:00", "percent": 20}]):
            with self.subTest(entries=entries), self.assertRaisesRegex(ValueError, "household.schedule"):
                HouseholdSchedule(entries)

    def test_yaml_preserves_original_schedule(self):
        schedule = HouseholdSchedule(load_settings()["light"]["household"]["schedule"])
        for hour in range(24):
            for minute in range(60):
                now = datetime(2026, 10, 26, hour, minute)
                self.assertAlmostEqual(schedule.ratio(now), household_ratio(now))

    def test_custom_yaml_schedule_reaches_output_calculation(self):
        settings = load_settings()
        settings["configurate"] = "lrkv_tt.yaml"
        settings["light"]["household"]["schedule"] = [{"time": "00:00", "percent": 25}]
        service = LightingService(settings)
        service.manager.items_by_id.clear()
        for index in range(20):
            service.manager._process_item({"name": str(index), "address": f"{index // 16 + 1}:{index % 16}", "algorithm": "domacnost"})
        service.model_clock.connected = True
        with patch("algorithms.monotonic", return_value=0), patch("hjop.monotonic", return_value=0):
            service.model_clock.apply_time("-;MOD-CAS;0;9;19:00:00;1".split(";"))
        self.assertEqual(sum(sum(ports.values()) for ports in service.daemon.desired.values()), 5)
        settings["light"]["household"]["schedule"] = []
        with self.assertRaisesRegex(ValueError, "household.schedule"):
            LightingService(settings)


if __name__ == "__main__":
    unittest.main()
