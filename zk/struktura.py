import yaml
import itertools

id_generator = itertools.count(1)


class PrvekStromu:
    """Základní třída pro všechny prvky, zajišťuje automatické unikátní ID."""

    def __init__(self):
        self.id = next(id_generator)


class SvetelnyOkruh(PrvekStromu):
    """Koncový uzel stromu - samotné světlo."""

    def __init__(self, data):
        super().__init__()
        self.nazev = data.get('nazev', 'Neznámý okruh')
        self.poznamka = data.get('poznamka', '')
        self.algoritmus = data.get('algoritmus', 'stale_sviti')

        # Zpracování adresy z formátu "1:5" na dva inty (modul a port)
        adresa_str = data.get('adresa', '0:0')
        try:
            casti = adresa_str.split(':')
            self.modul = int(casti[0])
            self.port = int(casti[1])
        except (ValueError, IndexError):
            # Ochrana proti překlepu v YAMLu (např. "1-5" nebo chybějící adresa)
            print(f"⚠️ Varování: Špatný formát adresy u '{self.nazev}' ({adresa_str}). Nastavuji Modul 0, Port 0.")
            self.modul = 0
            self.port = 0

    def vypis(self, odsa=""):
        print(
            f"{odsa}💡 [ID: {self.id}] {self.nazev} (Modul: {self.modul}, Port: {self.port}, Algoritmus: {self.algoritmus})")


class Skupina(PrvekStromu):
    """Univerzální uzel stromu (Kolejiště, Nádraží, Budova, Podskupina...).
       Může obsahovat další skupiny a světelné okruhy."""

    def __init__(self, data):
        super().__init__()
        self.nazev = data.get('nazev', 'Bez názvu')
        self.typ = data.get('typ', 'skupina')
        self.poznamka = data.get('poznamka', '')

        # Rekurzivně načteme všechny vnořené skupiny a okruhy
        self.skupiny = [Skupina(s) for s in data.get('skupiny', [])]
        self.okruhy = [SvetelnyOkruh(o) for o in data.get('okruhy', [])]

        # Specifická data jen pro kořenový uzel (kolejiště)
        self.verze = data.get('verze')
        self.datum = data.get('datum')

    def vypis(self, odsa=""):
        # Nastavení ikonky podle typu skupiny pro hezčí výpis
        ikony = {
            "kolejiste": "🛤️",
            "nadrazi": "🚉",
            "budova": "🏠",
            "podskupina": "📁"
        }
        ikona = ikony.get(self.typ, "📦")  # 📦 je výchozí, pokud typ neznáme

        if self.typ == "kolejiste":
            print(f"{ikona} [ID: {self.id}] Kolejiště: {self.nazev} (v{self.verze})")
            print("=" * 50)
        else:
            print(f"{odsa}{ikona} [ID: {self.id}] {self.nazev} (Typ: {self.typ})")

        # Výpis potomků (zanořování)
        for skupina in self.skupiny:
            skupina.vypis(odsa + "  ")
        for okruh in self.okruhy:
            okruh.vypis(odsa + "  ")


# ==========================================
# 2. FUNKCE PRO PROHLEDÁVÁNÍ STROMU
# ==========================================

def iteruj_strom(prvek):
    """Generátor: Projde zadaný prvek a všechny jeho potomky ve stromu."""
    yield prvek

    # Nyní je prohledávání mnohem jednodušší, ptáme se jen na skupiny a okruhy
    potomci = []
    if hasattr(prvek, 'skupiny'): potomci.extend(prvek.skupiny)
    if hasattr(prvek, 'okruhy'): potomci.extend(prvek.okruhy)

    for potomek in potomci:
        yield from iteruj_strom(potomek)


def najdi_prvek_podle_id(koren, hledane_id):
    """Najde ve stromu prvek s daným ID."""
    for prvek in iteruj_strom(koren):
        if prvek.id == hledane_id:
            return prvek
    return None


def ziskej_vsechna_id(koren, start_id):
    """Vrátí seznam všech ID pod zadaným prvkem (včetně samotného prvku)."""
    start_prvek = najdi_prvek_podle_id(koren, start_id)
    if not start_prvek:
        return []
    return [p.id for p in iteruj_strom(start_prvek)]


def ziskej_id_svetelnych_okruhu(koren, start_id):
    """Vrátí seznam ID, ale vyfiltruje POUZE světelné okruhy pod zadaným prvkem."""
    start_prvek = najdi_prvek_podle_id(koren, start_id)
    if not start_prvek:
        return []
    return [p.id for p in iteruj_strom(start_prvek) if isinstance(p, SvetelnyOkruh)]


# ==========================================
# 3. HLAVNÍ BĚH PROGRAMU
# ==========================================

def zmenStav(id, stav):
    for p in id:
        print(f"Prvek {p} má stav {stav}.")



if __name__ == "__main__":
    print("")