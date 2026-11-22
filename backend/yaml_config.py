"""Reading YAML files and reporting configuration structure errors."""
from pathlib import Path
import yaml


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



def read_mapping(source):
    source = Path(source)
    try:
        with source.open(encoding="utf-8") as file:
            value = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        location = f", řádek {mark.line + 1}, sloupec {mark.column + 1}" if mark else ""
        problem = getattr(exc, "problem", None) or str(exc)
        raise ConfigurationError(f"Neplatný YAML v souboru {source}{location}: {problem}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"Konfigurace {source}: očekávány YAML sekce.")
    return value
