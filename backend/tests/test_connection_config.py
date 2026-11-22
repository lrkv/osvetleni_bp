import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configurate import load_settings
from connection_config import HjopConfig, MtbConfig
from hjop import HjopClock
from mtb import DaemonClient
from service import LightingService
from yaml_config import ConfigurationError


class ConnectionConfigTests(unittest.TestCase):
    def test_service_passes_only_typed_connection_sections(self):
        settings = load_settings()
        service = LightingService(settings)
        self.assertIsInstance(service.model_clock.config, HjopConfig)
        self.assertIsInstance(service.daemon.config, MtbConfig)
        self.assertEqual(service.model_clock.config.host, settings['hjop']['host'])
        self.assertEqual(service.daemon.config.port, settings['mtb']['port'])
        self.assertEqual(service.use_hjop, settings['hjop']['enabled'])
        settings['hjop']['host'] = 'changed-after-construction'
        self.assertNotEqual(service.model_clock.config.host, settings['hjop']['host'])
        with self.assertRaises(FrozenInstanceError):
            service.model_clock.config.host = 'changed'

    def test_direct_construction_validates_values_without_defaults(self):
        settings = load_settings()
        for cls, section in ((HjopConfig, 'hjop'), (MtbConfig, 'mtb')):
            config = cls.from_mapping(settings[section])
            for field, value in (('port', True), ('port', '3841'), ('timeout', float('nan')), ('host', '')):
                with self.subTest(section=section, field=field), self.assertRaises(ConfigurationError):
                    replace(config, **{field: value})
            incomplete = dict(settings[section])
            del incomplete['host']
            with self.assertRaisesRegex(ConfigurationError, section + r'\.host'):
                cls.from_mapping(incomplete)
            with self.assertRaises(TypeError):
                cls()

    def test_callbacks_are_separate_from_yaml_configuration(self):
        settings = load_settings()
        calls = []
        clock = HjopClock(HjopConfig.from_mapping(settings['hjop']), on_change=lambda: calls.append('clock'))
        daemon = DaemonClient(MtbConfig.from_mapping(settings['mtb']), on_change=lambda: calls.append('mtb'))
        clock.on_change()
        daemon.on_change()
        self.assertEqual(calls, ['clock', 'mtb'])
