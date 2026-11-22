"""Typed, immutable settings for individual external connections."""
from dataclasses import dataclass, fields
from typing import Self

import math

from yaml_config import ConfigurationError, mapping, text


def integer(value, path):
    if type(value) is not int:
        raise ConfigurationError(f"Konfigurace {path}: očekáváno celé číslo.")


def positive(value, path, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0 or (integer and not isinstance(value, int))):
        raise ConfigurationError(f"Konfigurace {path}: očekáváno kladné {'celé číslo' if integer else 'číslo'}.")



def validate_connection(config, section, time_fields):
    text(config.host, section + ".host")
    integer(config.port, section + ".port")
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
class ServerConfig:
    host: str
    port: int

    def __post_init__(self):
        text(self.host, "server.host")
        integer(self.port, "server.port")

    @classmethod
    def from_mapping(cls, data) -> Self:
        mapping(data, (field.name for field in fields(cls)), "server")
        return cls(**data)
