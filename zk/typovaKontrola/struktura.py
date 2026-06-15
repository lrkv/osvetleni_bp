import yaml
import itertools

# ==========================================
# 1. GENERÁTOR ID A TŘÍDY PRO STROM
# ==========================================

# Generátor pro automatická ID (začíná od 1)
id_generator = itertools.count(1)


class PrvekStromu:
    """Základní třída pro všechny prvky, zajišťuje automatické unikátní ID."""

    def __init__(self):
        self.id = next(id_generator)


class SvetelnyOkruh(PrvekStromu):
    def __init__(self, data):
        super().__init__()
        self.nazev = data.get('nazev')
        self.adresa = data.get('adresa')
        self.poznamka = data.get('poznamka')
        self.algoritmus = data.get('algoritmus')

    def vypis(self, odsa=""):
        print(f"{odsa}💡 [ID: {self.id}] {self.nazev} (Adresa: {self.adresa}, Algoritmus: {self.algoritmus})")


class Podskupina(PrvekStromu):
    def __init__(self, data):
        super().__init__()
        self.nazev = data.get('nazev')
        self.svetelne_okruhy = [SvetelnyOkruh(okruh) for okruh in data.get('svetelne_okruhy', [])]

    def vypis(self, odsa=""):
        print(f"{odsa}📁 [ID: {self.id}] Podskupina: {self.nazev}")
        for okruh in self.svetelne_okruhy:
            okruh.vypis(odsa + "  ")


class Budova(PrvekStromu):
    def __init__(self, data):
        super().__init__()
        self.nazev = data.get('nazev')
        self.poznamka = data.get('poznamka')
        self.podskupiny = [Podskupina(p) for p in data.get('podskupiny', [])]
        self.svetelne_okruhy = [SvetelnyOkruh(o) for o in data.get('svetelne_okruhy', [])]

    def vypis(self, odsa=""):
        print(f"{odsa}🏠 [ID: {self.id}] Budova: {self.nazev}")
        for podskupina in self.podskupiny:
            podskupina.vypis(odsa + "  ")
        for okruh in self.svetelne_okruhy:
            okruh.vypis(odsa + "  ")


class Nadrazi(PrvekStromu):
    def __init__(self, data):
        super().__init__()
        self.nazev = data.get('nazev')
        self.poznamka = data.get('poznamka')
        self.budovy = [Budova(b) for b in data.get('budovy', [])]
        self.svetelne_okruhy = [SvetelnyOkruh(o) for o in data.get('svetelne_okruhy', [])]

    def vypis(self, odsa=""):
        print(f"{odsa}🚉 [ID: {self.id}] Nádraží: {self.nazev}")
        for budova in self.budovy:
            budova.vypis(odsa + "  ")
        for okruh in self.svetelne_okruhy:
            okruh.vypis(odsa + "  ")


class Kolejiste(PrvekStromu):
    def __init__(self, data):
        super().__init__()
        k_data = data.get('kolejiste', {})
        self.nazev = k_data.get('nazev')
        self.verze = k_data.get('verze')
        self.datum = k_data.get('datum')
        self.poznamka = k_data.get('poznamka')
        self.nadrazi = [Nadrazi(n) for n in k_data.get('nadrazi', [])]

    def vypis(self):
        print(f"🛤️ [ID: {self.id}] Kolejiště: {self.nazev} (v{self.verze})")
        print("=" * 50)
        for nadrazi in self.nadrazi:
            nadrazi.vypis("  ")


# ==========================================
# 2. FUNKCE PRO PROHLEDÁVÁNÍ STROMU
# ==========================================

def iteruj_strom(prvek):
    """Generátor: Projde zadaný prvek a všechny jeho potomky ve stromu."""
    yield prvek

    potomci = []
    if hasattr(prvek, 'nadrazi'): potomci.extend(prvek.nadrazi)
    if hasattr(prvek, 'budovy'): potomci.extend(prvek.budovy)
    if hasattr(prvek, 'podskupiny'): potomci.extend(prvek.podskupiny)
    if hasattr(prvek, 'svetelne_okruhy'): potomci.extend(prvek.svetelne_okruhy)

    for potomek in potomci:
        yield from iteruj_strom(potomek)


def najdi_prvek_podle_id(kolejiste, hledane_id):
    """Najde ve stromu prvek s daným ID."""
    for prvek in iteruj_strom(kolejiste):
        if prvek.id == hledane_id:
            return prvek
    return None


def ziskej_vsechna_id(kolejiste, start_id):
    """Vrátí seznam všech ID pod zadaným prvkem (včetně samotného prvku)."""
    start_prvek = najdi_prvek_podle_id(kolejiste, start_id)
    if not start_prvek:
        return []
    return [p.id for p in iteruj_strom(start_prvek)]


def ziskej_id_svetelnych_okruhu(kolejiste, start_id):
    """Vrátí seznam ID, ale vyfiltruje POUZE světelné okruhy pod zadaným prvkem."""
    start_prvek = najdi_prvek_podle_id(kolejiste, start_id)
    if not start_prvek:
        return []
    return [p.id for p in iteruj_strom(start_prvek) if isinstance(p, SvetelnyOkruh)]


# ==========================================
# 3. HLAVNÍ BĚH PROGRAMU
# ==========================================

soubor_s_daty = "data2.yaml"

if __name__ == "__main__":
    try:
        # Načtení dat
        with open(soubor_s_daty, 'r', encoding='utf-8') as soubor:
            data = yaml.safe_load(soubor)

        # Vytvoření stromové struktury v paměti
        moje_kolejiste = Kolejiste(data)

        # 1. Výpis kompletní struktury do konzole pro kontrolu
        moje_kolejiste.vypis()

        while True:
            vstup = input("Zadej ID: ")
            testovaci_id = int(vstup)

            nalezeny_prvek = najdi_prvek_podle_id(moje_kolejiste, testovaci_id)
            if nalezeny_prvek:
                print(f"Byl vybrán uzel: {nalezeny_prvek.nazev} (ID: {testovaci_id})")

                # Získání VŠECH ID
                id_vse = ziskej_vsechna_id(moje_kolejiste, testovaci_id)
                print(f"-> Všechna ID pod tímto uzlem: {id_vse}")

                # Získání JEN OKRUHŮ
                id_svetla = ziskej_id_svetelnych_okruhu(moje_kolejiste, testovaci_id)
                print(f"-> Z toho pouze ID světelných okruhů: {id_svetla}")
            else:
                print(f"Prvek s ID {testovaci_id} neexistuje.")

    except FileNotFoundError:
        print(f"❌ CHYBA: Soubor '{soubor_s_daty}' nebyl nalezen. Zkontroluj, že je ve stejné složce.")
    except yaml.YAMLError as chyba:
        print(f"❌ CHYBA: Soubor '{soubor_s_daty}' obsahuje neplatný YAML formát.\nDetail: {chyba}")