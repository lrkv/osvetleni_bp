"""Typed, immutable settings for individual external connections."""
from dataclasses import dataclass, fields
from typing import Self

from settings_validation import ConfigurationError, mapping, positive, text


def validate_connection(config, section, time_fields):
    text(config.host, section + ".host")
    positive(config.port, section + ".port", integer=True)
    if config.port > 65535:
        raise ConfigurationError(f"Konfigurace {section}.port: port musí být nejvýše 65535.")
    for key in time_fields:
        positive(getattr(config, key), section + "." + key)


@dataclass(frozen=True, slots=True)
class HjopConfig:
    enabled: bool
    host: str
    port: int
    timeout: float
    reconnect_delay: float
    idle_timeout: float
    sync_timeout: float

    def __post_init__(self):
        if not isinstance(self.enabled, bool):
            raise ConfigurationError("Konfigurace hjop.enabled: očekáváno true nebo false.")
        validate_connection(self, "hjop", ("timeout", "reconnect_delay", "idle_timeout", "sync_timeout"))

    @classmethod
    def from_mapping(cls, data) -> Self:
        mapping(data, (field.name for field in fields(cls)), "hjop")
        return cls(**data)


@dataclass(frozen=True, slots=True)
class MtbConfig:
    host: str
    port: int
    timeout: float
    reconnect_delay: float

    def __post_init__(self):
        validate_connection(self, "mtb", ("timeout", "reconnect_delay"))

    @classmethod
    def from_mapping(cls, data) -> Self:
        mapping(data, (field.name for field in fields(cls)), "mtb")
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ConnectionConfigs:
    hjop: HjopConfig
    mtb: MtbConfig
