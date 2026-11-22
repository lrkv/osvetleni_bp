import sys
import tempfile
import unittest
import yaml
import copy
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configurate import BASE_DIR, load_settings
from service import LightingService


class SettingsTests(unittest.TestCase):
    def test_split_files_resolve_relative_to_config_and_apply_corridor_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = {"layout": {"file": "layout.yaml"}, "algorithms_file": "timing.yaml"}
            config.update({key: load_settings()[key] for key in ("server", "mtb", "hjop")})
            (root / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
            (root / "layout.yaml").write_text('groups: [{name: Hall, address: "1:0", algorithm: chodba}]', encoding="utf-8")
            light = load_settings()["light"]
            light.update(sunrise="06:00", sunset="20:00")
            light["corridor"].update(pause_min_seconds=1, pause_max_seconds=1, min_on_seconds=42, max_on_seconds=42)
            (root / "timing.yaml").write_text(yaml.safe_dump(light), encoding="utf-8")
            settings = load_settings(root / "config.yaml")
            # Windows may return either the short (8.3) or full form of a path.
            self.assertTrue(Path(settings["configurate"]).samefile(root / "layout.yaml"))
            service = LightingService(settings)
            now = datetime(2026, 10, 29, 22)
            with patch("algorithm.corridor.monotonic", return_value=0):
                service.manager.calculate_outputs(service.sunrise, service.sunset, now=now)
            with patch("algorithm.corridor.monotonic", return_value=1):
                service.manager.calculate_outputs(service.sunrise, service.sunset, now=now)
            corridor = service.manager._corridors[1]
            self.assertTrue(corridor.is_on)
            self.assertEqual(corridor.deadline, 43)

    def test_missing_unknown_and_invalid_settings_are_rejected(self):
        complete = load_settings()
        for section in ("server", "mtb", "hjop"):
            for key in complete[section]:
                settings = copy.deepcopy(complete)
                del settings[section][key]
                with self.subTest(section=section, key=key), self.assertRaisesRegex(ValueError, section + r"\." + key):
                    LightingService(settings)
        for section in ("corridor", "household", "shop"):
            for key in complete["light"][section]:
                settings = copy.deepcopy(complete)
                del settings["light"][section][key]
                with self.subTest(section=section, key=key), self.assertRaisesRegex(ValueError, section + r"\." + key):
                    LightingService(settings)
        settings = copy.deepcopy(complete)
        settings["light"]["corridor"]["pause_min_second"] = 60
        with self.assertRaisesRegex(ValueError, "pause_min_second"):
            LightingService(settings)
        for section, key, value in (("hjop", "enabled", "false"), ("mtb", "port", True),
                                    ("mtb", "timeout", float("nan")), ("server", "port", "8000")):
            settings = copy.deepcopy(complete)
            settings[section][key] = value
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                LightingService(settings)

    def test_missing_or_invalid_algorithms_file_does_not_silently_use_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config.yaml"
            data = {"layout": {"file": "layout.yaml"}, "algorithms_file": "timing.yaml"}
            data.update({key: load_settings()[key] for key in ("server", "mtb", "hjop")})
            config.write_text(yaml.safe_dump(data), encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                load_settings(config)
            (root / "timing.yaml").write_text('[]', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_settings(config)

    def test_corridor_rejects_invalid_on_interval(self):
        settings = load_settings()
        settings["light"]["corridor"]["min_on_seconds"] = 40
        settings["light"]["corridor"]["max_on_seconds"] = 20
        with self.assertRaises(ValueError):
            LightingService(settings)

    def test_default_settings_load_from_config_independent_of_working_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("pathlib.Path.cwd", return_value=Path(folder)):
                settings = load_settings()
        self.assertEqual(Path(settings["configurate"]).parent, BASE_DIR / "config")
        self.assertTrue(Path(settings["configurate"]).is_file())
        self.assertIn("sunrise", settings["light"])
        self.assertIn("household", settings["light"])
