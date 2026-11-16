"""Strict validation shared by YAML loading and application construction."""
import math
import re


class ConfigurationError(ValueError):
    pass


def mapping(value, keys, path):
    keys = set(keys)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Konfigurace {path}: očekávána sekce s položkami.")
    missing = set(keys) - value.keys()
    unknown = value.keys() - set(keys)
    if missing or unknown:
        details = []
        if missing:
            details.append("chybí " + ", ".join(f"{path}.{key}" for key in sorted(missing)))
        if unknown:
            details.append("neznámé položky " + ", ".join(f"{path}.{key}" for key in sorted(unknown, key=str)))
        raise ConfigurationError("Konfigurace: " + "; ".join(details))


def text(value, path):
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"Konfigurace {path}: očekáván neprázdný text.")


def positive(value, path, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0 or (integer and not isinstance(value, int))):
        raise ConfigurationError(f"Konfigurace {path}: očekáváno kladné {'celé číslo' if integer else 'číslo'}.")


def validate_light(light):
    mapping(light, ('sunrise', 'sunset', 'corridor', 'household', 'shop'), 'light')
    for key in ('sunrise', 'sunset'):
        if not isinstance(light[key], str) or not re.fullmatch(r'(?:[01]?\d|2[0-3]):[0-5]\d', light[key], re.ASCII):
            raise ConfigurationError(f"Konfigurace light.{key}: očekáván čas HH:MM.")
    mapping(light['corridor'], ('min_on_seconds', 'max_on_seconds', 'pause_min_seconds', 'pause_max_seconds'), 'corridor')
    mapping(light['household'], ('min_on_seconds', 'max_on_seconds', 'min_off_seconds', 'schedule'), 'household')
    mapping(light['shop'], ('opening_time', 'closing_time'), 'shop')
    # Validate intervals and schedule using their owning algorithm classes.
    from algorithm import CorridorLighting, HouseholdLighting, Shop
    CorridorLighting(**light['corridor'])
    HouseholdLighting(**light['household'])
    Shop(**light['shop'])


def validate_settings(settings):
    mapping(settings, ('configurate', 'light', 'server', 'mtb', 'hjop'), 'config')
    text(settings['configurate'], 'layout.file')
    server = settings['server']
    mapping(server, ('host', 'port', 'allowed_origins', 'allowed_origin_regex'), 'server')
    from connection_config import HjopConfig, MtbConfig, ConnectionConfigs
    connections = ConnectionConfigs(
        hjop=HjopConfig.from_mapping(settings['hjop']),
        mtb=MtbConfig.from_mapping(settings['mtb']),
    )
    text(server['host'], 'server.host')
    for section in ('server',):
        port = settings[section]['port']
        positive(port, section + '.port', integer=True)
        if port > 65535:
            raise ConfigurationError(f'Konfigurace {section}.port: port musí být nejvýše 65535.')
    if not isinstance(server['allowed_origins'], list) or any(not isinstance(item, str) or not item for item in server['allowed_origins']):
        raise ConfigurationError('Konfigurace server.allowed_origins: očekáván seznam adres.')
    regex = server['allowed_origin_regex']
    if regex is not None:
        text(regex, 'server.allowed_origin_regex')
        try:
            re.compile(regex)
        except re.error as exc:
            raise ConfigurationError(f'Konfigurace server.allowed_origin_regex: {exc}') from exc
    validate_light(settings['light'])
    return connections
