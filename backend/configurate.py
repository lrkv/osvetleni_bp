import yaml

def load_configuration(file_source: str = 'config.yaml'):
    with open(file_source, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)

    return data['light']['sunrise'], data['light']['sunset'], data['configurate']

class ConfigManager:
    def __init__(self):
        self.tree_data = {}             # Stromová struktura pro web
        self.items_by_id = {}           # Plochý slovník pro rychlé hledání prvků podle ID
        self.next_id = 1                # Počítadlo pro generování unikátních ID

    def _generate_id(self):
        current_id = self.next_id
        self.next_id += 1
        return current_id

    def load_yaml(self, file_path='railway00.yaml'):
        # Načtení YAML souboru
        with open(file_path, 'r', encoding='utf-8') as file:
            self.tree_data = yaml.safe_load(file)

        # Projdeme hlavní skupiny z YAMLu a postupně jim přiřadíme ID
        if 'groups' in self.tree_data:
            for group in self.tree_data['groups']:
                self._process_item(group)

        return self.tree_data, self.items_by_id

    def _process_item(self, item):
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
            item['algorithm'] = new_algorithm

        # Pokud má prvek vnořené položky (je to skupina), propíšeme změnu i do nich
        if 'items' in item:
            for child in item['items']:
                self._apply_algorithm(child, new_algorithm)

    def update_hardware(self, daemon, sunrise: str, sunset: str):
        """
        Zkompletuje hodnoty pro všechna světla a odešle je příslušným modulům.
        """
        # Slovník, kde klíč je číslo modulu a hodnota je slovník portů a jejich stavů
        # Příklad naplnění: {1: {0: 1, 1: 0, 12: 60}}
        modules_payload = {}

        for item_id, item in self.items_by_id.items():
            # Zajímá nás jen prvek, který má fyzickou adresu a přiřazený algoritmus
            if 'address' in item and 'algorithm' in item:

                # Rozdělení adresy z formátu "1:12" na modul a port
                address_parts = item['address'].split(':')
                if len(address_parts) != 2:
                    continue  # Pokud je adresa zapsaná špatně, prvek přeskočíme

                module_addr = int(address_parts[0])
                port = int(address_parts[1])

                # Výpočet stavu (0, 1, nebo 60) podle vybraného algoritmu
                from algorithms import evaluate_algorithm
                output_val = evaluate_algorithm(item['algorithm'], sunrise, sunset)

                # NOVÉ: Uložení logického stavu přímo do prvku.
                # Pokud je hodnota větší než 0 (svítí nebo bliká), bude is_on = True.
                item['is_on'] = output_val > 0

                # Pokud modul ještě v payloadu nemáme, založíme mu prázdný slovník pro porty
                if module_addr not in modules_payload:
                    modules_payload[module_addr] = {}

                # Zapíšeme vypočítanou hodnotu ke konkrétnímu portu
                modules_payload[module_addr][port] = output_val

        # Projdeme připravený payload a rozešleme ho po modulech
        if daemon is not None:
            for module_addr, ports_data in modules_payload.items():
                try:
                    # Odesílá se přesně ve formátu: daemon.set_outputs(1, {0: 1, 1: 0})
                    daemon.set_outputs(module_address=module_addr, outputs_data=ports_data)
                except Exception as e:
                    print(f"Chyba při odesílání na modul {module_addr}: {e}")