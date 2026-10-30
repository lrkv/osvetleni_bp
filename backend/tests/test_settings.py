import sys
import tempfile
import unittest
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
            (root / "config.yaml").write_text('layout: {file: layout.yaml}\nalgorithms_file: timing.yaml\n', encoding="utf-8")
            (root / "layout.yaml").write_text('groups: [{name: Hall, address: "1:0", algorithm: chodba}]', encoding="utf-8")
            (root / "timing.yaml").write_text('sunrise: "06:00"\nsunset: "20:00"\ncorridor: {pause_min_seconds: 1, pause_max_seconds: 1, min_on_seconds: 42, max_on_seconds: 42}', encoding="utf-8")
            settings = load_settings(root / "config.yaml")
            self.assertEqual(Path(settings["configurate"]), root / "layout.yaml")
            service = LightingService(settings)
            now = datetime(2026, 10, 29, 22)
            with patch("algorithms.monotonic", return_value=0):
                service.manager.calculate_outputs(service.sunrise, service.sunset, now=now)
            with patch("algorithms.monotonic", return_value=1):
                service.manager.calculate_outputs(service.sunrise, service.sunset, now=now)
            corridor = service.manager._corridors[1]
            self.assertTrue(corridor.is_on)
            self.assertEqual(corridor.deadline, 43)

    def test_old_single_file_and_czech_key_are_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config.yaml"
            config.write_text('configurate: old.yaml\nlight: {sunrise: "06:00", sunset: "20:00", chodba: {pause_min_seconds: 99}}', encoding="utf-8")
            settings = load_settings(config)
            self.assertEqual(settings["configurate"], "old.yaml")
            self.assertEqual(settings["light"]["corridor"]["pause_min_seconds"], 99)
            self.assertNotIn("chodba", settings["light"])

    def test_missing_or_invalid_algorithms_file_does_not_silently_use_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config.yaml"
            config.write_text('algorithms_file: timing.yaml', encoding="utf-8")
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

    def test_default_settings_load_from_configurate_independent_of_working_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("pathlib.Path.cwd", return_value=Path(folder)):
                settings = load_settings()
        self.assertEqual(Path(settings["configurate"]).parent, BASE_DIR / "configurate")
        self.assertTrue(Path(settings["configurate"]).is_file())
        self.assertIn("sunrise", settings["light"])
        self.assertIn("household", settings["light"])
