import logging
from pathlib import Path
from datetime import datetime

import yaml
from functools import partial
from settings_validation import mapping, validate_settings, validate_light
from algorithm import ALGORITHMS, CorridorLighting, HouseholdLighting, Shop

logger = logging.getLogger(__name__)

SYSTEM_TIME = object()

BASE_DIR = Path(__file__).resolve().parent
SUPPORTED_ALGORITHMS = tuple(ALGORITHMS)


def load_settings(file_source=None):
    path = Path(file_source) if file_source else BASE_DIR / "config" / "config.yaml"
    path = path.resolve()

    def read_mapping(source):
        with source.open(encoding="utf-8") as file:
            value = yaml.safe_load(file)
        if not isinstance(value, dict):
            raise ValueError(f"Konfigurace {source} musí obsahovat YAML sekce.")
        return value

    data = read_mapping(path)
    mapping(data, ('layout', 'algorithms_file', 'server', 'mtb', 'hjop'), str(path))
    mapping(data['layout'], ('file',), 'layout')
    from settings_validation import text
    text(data['layout']['file'], 'layout.file')
    text(data['algorithms_file'], 'algorithms_file')
    algorithms_path = path.parent / data.pop('algorithms_file')
    light = read_mapping(algorithms_path)
    data['configurate'] = str((path.parent / data.pop('layout')['file']).resolve())
    data['light'] = light
    try:
        validate_settings(data)
    except ValueError as exc:
        raise ValueError(f"Konfigurace {path} / {algorithms_path}: {exc}") from exc
    return data


class ConfigManager:
    def __init__(self, corridor_pause_min, corridor_pause_max, *,
                 corridor_min_on_seconds, corridor_max_on_seconds,
                 household_min_on_seconds, household_max_on_seconds, household_min_off_seconds, household_schedule,
                 shop_opening_time, shop_closing_time):
        # Validate once, before any background task is started.
        CorridorLighting(corridor_pause_min, corridor_pause_max, corridor_min_on_seconds, corridor_max_on_seconds)
        self.corridor_min_on_seconds = corridor_min_on_seconds
        self.corridor_max_on_seconds = corridor_max_on_seconds
        self.corridor_pause_min = corridor_pause_min
        self.corridor_pause_max = corridor_pause_max
        Shop(shop_opening_time, shop_closing_time)
        self._factories = dict(ALGORITHMS)
        self._factories[Shop.identifier] = partial(Shop, shop_opening_time, shop_closing_time)
        self._factories[CorridorLighting.identifier] = partial(
            CorridorLighting, corridor_pause_min, corridor_pause_max,
            corridor_min_on_seconds, corridor_max_on_seconds)
        self._factories[HouseholdLighting.identifier] = partial(
            HouseholdLighting, household_min_on_seconds, household_max_on_seconds,
            household_min_off_seconds, schedule=household_schedule)
        self._shared = {key: self._factories[key]() for key, cls in ALGORITHMS.items() if cls.shared}
        self._households = self._shared[HouseholdLighting.identifier]
        self._instances = {}
        self._last_outputs = {}
        self.tree_data = {}             # Stromová struktura pro web
        self.items_by_id = {}           # Plochý slovník pro rychlé hledání prvků podle ID
        self.next_id = 1                # Počítadlo pro generování unikátních ID

    @classmethod
    def from_settings(cls, light):
        validate_light(light)
        corridor, household, shop = light['corridor'], light['household'], light['shop']
        return cls(corridor['pause_min_seconds'], corridor['pause_max_seconds'],
                   corridor_min_on_seconds=corridor['min_on_seconds'],
                   corridor_max_on_seconds=corridor['max_on_seconds'],
                   household_min_on_seconds=household['min_on_seconds'],
                   household_max_on_seconds=household['max_on_seconds'],
                   household_min_off_seconds=household['min_off_seconds'],
                   household_schedule=household['schedule'],
                   shop_opening_time=shop['opening_time'], shop_closing_time=shop['closing_time'])

    def _generate_id(self):
        current_id = self.next_id
        self.next_id += 1
        return current_id

    def load_yaml(self, file_path='railway00.yaml'):
        self._instances.clear()
        for instance in self._shared.values():
            instance.reset()
        self._last_outputs.clear()
        self.items_by_id.clear()
        self.next_id = 1
        # Načtení YAML souboru
        with open(file_path, 'r', encoding='utf-8') as file:
            self.tree_data = yaml.safe_load(file)

        # Projdeme hlavní skupiny z YAMLu a postupně jim přiřadíme ID
        if 'groups' in self.tree_data:
            for group in self.tree_data['groups']:
                self._process_item(group)

        return self.tree_data, self.items_by_id

    def _process_item(self, item):
        # Accept the historical typo, but expose only the canonical key to the UI.
        if 'adress' in item:
            if 'address' in item and item['address'] != item['adress']:
                raise ValueError(f"Rozdílné address a adress u prvku {item.get('name')!r}.")
            item['address'] = item.pop('adress')
            logger.warning("Prvek %r: použito 'adress'; v YAML opravte na 'address'.", item.get('name'))
        # 1. Vygenerování a uložení ID přímo do prvku
        item_id = self._generate_id()
        item['id'] = item_id

        # 2. Uložení celého prvku do plochého slovníku pod jeho ID
        self.items_by_id[item_id] = item

        # 3. Pokud má prvek vnořené 'items', projdeme je rekurzivně
        if 'items' in item:
            for child in item['items']:
                self._process_item(child)

    def change_algorithm(self, target_id: int, new_algorithm: str) -> bool:
        if new_algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError('Neznámý algoritmus.')
        # Vyhledání prvku podle ID v našem rychlém plochém seznamu
        item = self.items_by_id.get(target_id)
        if not item:
            return False

        # Spuštění interní funkce pro aplikování změny
        self._apply_algorithm(item, new_algorithm)
        return True

    def _apply_algorithm(self, item: dict, new_algorithm: str) -> None:
        # Pokud má prvek adresu, jedná se o koncové světlo -> změníme algoritmus
        if 'address' in item:
            if item.get('algorithm') != new_algorithm:
                self._instances.pop(item['id'], None)
                for instance in self._shared.values():
                    instance.forget(item['id'])
            item['algorithm'] = new_algorithm

        # Pokud má prvek vnořené položky (je to skupina), propíšeme změnu i do nich
        if 'items' in item:
            for child in item['items']:
                self._apply_algorithm(child, new_algorithm)

    @property
    def _corridors(self):
        # Compatibility view for tools inspecting corridor timers.
        return {key: value for key, value in self._instances.items()
                if isinstance(value, CorridorLighting)}

    def algorithm_for(self, item):
        identifier = item.get('algorithm')
        if identifier not in self._factories:
            return None
        instance = self._instances.get(item['id'])
        if instance is None or instance.identifier != identifier:
            instance = self._shared.get(identifier)
            if instance is None:
                instance = self._factories[identifier]()
            self._instances[item['id']] = instance
        return instance

    def calculate_outputs(self, sunrise: str, sunset: str, *, now=SYSTEM_TIME):
        """Dispatch through the common algorithm interface without network I/O."""
        now = datetime.now() if now is SYSTEM_TIME else now
        modules = {}
        for identifier, instance in self._shared.items():
            members = [item['id'] for item in self.items_by_id.values()
                       if 'address' in item and item.get('algorithm') == identifier]
            instance.prepare(members, now)
        for item in self.items_by_id.values():
            if 'address' not in item:
                continue
            module, port = map(int, item['address'].split(':'))
            instance = self.algorithm_for(item)
            if instance is None:
                error = f"Nepodporovaný algoritmus {item.get('algorithm')!r}; výstup je vypnutý."
                if item.get('configuration_error') != error:
                    logger.warning("%s (%s): %s", item.get('name'), item['address'], error)
                item['configuration_error'] = error
                self._instances.pop(item['id'], None)
                output = 0
            else:
                item.pop('configuration_error', None)
                if now is None and instance.time_required:
                    output = self._last_outputs.get(item['id'], 0)
                else:
                    output = instance.compute(now, sunrise, sunset, item_id=item['id'])
            self._last_outputs[item['id']] = output
            item['is_on'] = output > 0
            modules.setdefault(module, {})[port] = output
        return modules
