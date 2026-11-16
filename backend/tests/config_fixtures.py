"""Test factories take baseline values from the checked-in YAML, never production fallbacks."""
from configurate import ConfigManager, load_settings
from algorithm import CorridorLighting, HouseholdLighting
from algorithm.household import household_ratio
from hjop import HjopClock
from mtb import DaemonClient


def construct(cls, values, args, overrides):
    values = dict(values)
    for key, value in zip(values, args):
        values[key] = value
    values.update(overrides)
    return cls(**values)


def make_manager(*args, **overrides):
    light = load_settings()['light']
    c, h, s = light['corridor'], light['household'], light['shop']
    values = dict(corridor_pause_min=c['pause_min_seconds'], corridor_pause_max=c['pause_max_seconds'],
                  corridor_min_on_seconds=c['min_on_seconds'], corridor_max_on_seconds=c['max_on_seconds'],
                  household_min_on_seconds=h['min_on_seconds'], household_max_on_seconds=h['max_on_seconds'],
                  household_min_off_seconds=h['min_off_seconds'], household_schedule=h['schedule'],
                  shop_opening_time=s['opening_time'], shop_closing_time=s['closing_time'])
    return construct(ConfigManager, values, args, overrides)


def make_corridor(*args, **overrides):
    c = load_settings()['light']['corridor']
    values = {key: c[key] for key in ('pause_min_seconds', 'pause_max_seconds', 'min_on_seconds', 'max_on_seconds')}
    return construct(CorridorLighting, values, args, overrides)


def make_household(*args, **overrides):
    return construct(HouseholdLighting, load_settings()['light']['household'], args, overrides)


def make_hjop(*args, **overrides):
    values = load_settings()['hjop']
    del values['enabled']
    return construct(HjopClock, values, args, overrides)


def make_daemon(*args, **overrides):
    return construct(DaemonClient, load_settings()['mtb'], args, overrides)


def configured_ratio(now):
    return household_ratio(now, load_settings()['light']['household']['schedule'])
