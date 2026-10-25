import logging
from pathlib import Path

import yaml
from algorithms import CorridorLighting, evaluate_algorithm

logger = logging.getLogger(__name__)

SYSTEM_TIME = object()
STATIC_ALGORITHMS = {"trvale_zapnuto", "trvale_vypnuto", "vyloha", "disco"}

BASE_DIR = Path(__file__).resolve().parent
SUPPORTED_ALGORITHMS = ("trvale_zapnuto", "trvale_vypnuto", "domacnost", "poulicni_lampa", "drazni_osvetleni", "byt", "chodba", "prodejna", "vyloha", "disco")


def load_settings(file_source=None):
    path = Path(file_source) if file_source else BASE_DIR / "config.yaml"
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_configuration(file_source=None):
    data = load_settings(file_source)
    return data['light']['sunrise'], data['light']['sunset'], data['configurate']


class ConfigManager:
    def __init__(self, corridor_pause_min=60, corridor_pause_max=300):
        # Validate once, before any background task is started.
        CorridorLighting(corridor_pause_min, corridor_pause_max)
        self.corridor_pause_min = corridor_pause_min
        self.corridor_pause_max = corridor_pause_max
        self._corridors = {}
        self._last_outputs = {}
        self.tree_data = {}             # Stromová struktura pro web
        self.items_by_id = {}           # Plochý slovník pro rychlé hledání prvků podle ID
        self.next_id = 1                # Počítadlo pro generování unikátních ID

    def _generate_id(self):
        current_id = self.next_id
        self.next_id += 1
        return current_id

    def load_yaml(self, file_path='railway00.yaml'):
        self._corridors.clear()
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

    def print_structure(self, item=None, level=0):
        # Pokud nepošleme konkrétní prvek, tiskneme od úplného začátku
        if item is None:
            layout_name = self.tree_data.get('layout_name', 'Kolejiště')
            print(f"=== {layout_name} ===")

            if 'groups' in self.tree_data:
                for group in self.tree_data['groups']:
                    self.print_structure(group, level + 1)
            return

        indent = "  " * level
        item_id = item.get('id')
        name = item.get('name')

        # Rozlišení, jestli jde o fyzické světlo (má adresu) nebo jen skupinu
        if 'address' in item:
            address = item.get('address')
            algorithm = item.get('algorithm')
            print(f"{indent}[ID: {item_id:02d}] Světlo: {name} (Adresa: {address}, Algoritmus: {algorithm})")
        else:
            print(f"{indent}[ID: {item_id:02d}] Skupina: {name}")

        # Pokud jsme ve skupině, vytiskneme postupně i její potomky
        if 'items' in item:
            for child in item['items']:
                self.print_structure(child, level + 1)

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
                self._corridors.pop(item['id'], None)
            item['algorithm'] = new_algorithm

        # Pokud má prvek vnořené položky (je to skupina), propíšeme změnu i do nich
        if 'items' in item:
            for child in item['items']:
                self._apply_algorithm(child, new_algorithm)

    def calculate_outputs(self, sunrise: str, sunset: str, *, now=SYSTEM_TIME):
        """Compute desired states without any network I/O."""
        modules = {}
        time_args = {} if now is SYSTEM_TIME else {"now": now}
        for item in self.items_by_id.values():
            if 'address' not in item:
                continue
            module, port = map(int, item['address'].split(':'))
            algorithm = item.get('algorithm')
            if algorithm != 'chodba':
                self._corridors.pop(item['id'], None)
            if algorithm not in SUPPORTED_ALGORITHMS:
                error = f"Nepodporovaný algoritmus {algorithm!r}; výstup je vypnutý."
                if item.get('configuration_error') != error:
                    logger.warning("%s (%s): %s", item.get('name'), item['address'], error)
                item['configuration_error'] = error
                output = 0  # Preserve the original fallback without preventing startup.
            else:
                item.pop('configuration_error', None)
                if now is None and algorithm not in STATIC_ALGORITHMS:
                    output = self._last_outputs.get(item['id'], 0)
                elif algorithm == 'chodba':
                    if item['id'] not in self._corridors:
                        self._corridors[item['id']] = CorridorLighting(
                            self.corridor_pause_min, self.corridor_pause_max)
                    output = evaluate_algorithm(algorithm, sunrise, sunset,
                                                corridor=self._corridors[item['id']], **time_args)
                else:
                    output = evaluate_algorithm(algorithm, sunrise, sunset, **time_args)
            self._last_outputs[item['id']] = output
            item['is_on'] = output > 0
            modules.setdefault(module, {})[port] = output
        return modules
