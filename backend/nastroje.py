import yaml
import json
import zoneinfo
from modely import Prvek, KoncovyPrvek
from datetime import datetime, timedelta, date

def nacti_strukturu(cesta_yaml):
    with open(cesta_yaml, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)['kolejiste']

    mapa_id = {}  # Slovník pro rychlé hledání: {id: objekt}
    self_counter = 1  # Počítadlo pro automatická ID

    def generuj_id():
        nonlocal self_counter
        id_ted = self_counter
        self_counter += 1
        return id_ted

    kolejiste_root = Prvek(0, "Celé kolejiště")
    mapa_id[0] = kolejiste_root

    for k_stanice, v_stanice in cfg.items():
        # Vytvoření stanice
        s_id = generuj_id()
        stanice = Prvek(s_id, v_stanice['nazev'], v_stanice.get('poznamka', ""))
        mapa_id[s_id] = stanice

        for k_prvku, v_prvku in v_stanice['prvky'].items():
            # Rozlišení: Budova (slovník s pod-prvky) vs Přímý okruh
            if 'algoritmus' in v_prvku:
                # Je to samostatný okruh ve stanici
                o_id = generuj_id()
                okruh = KoncovyPrvek(
                    o_id, v_prvku['nazev'], v_prvku['adresa'], v_prvku['port'],
                    v_prvku.get('popis', ""), v_prvku['algoritmus'], v_prvku.get('poznamka', "")
                )
                mapa_id[o_id] = okruh
                stanice.pridej(okruh)
            else:
                # Je to budova
                b_id = generuj_id()
                budova = Prvek(b_id, v_prvku['nazev'], v_prvku.get('poznamka', ""))
                mapa_id[b_id] = budova

                # Projdeme okruhy uvnitř budovy
                for k_sub, v_sub in v_prvku.items():
                    if isinstance(v_sub, dict) and 'algoritmus' in v_sub:
                        o_id = generuj_id()
                        okruh = KoncovyPrvek(
                            o_id, v_sub['nazev'], v_sub['adresa'], v_sub['port'],
                            v_sub.get('popis', ""), v_sub['algoritmus'], v_sub.get('poznamka', "")
                        )
                        mapa_id[o_id] = okruh
                        budova.pridej(okruh)
                stanice.pridej(budova)

        kolejiste_root.pridej(stanice)

    # Vracíme jak strom, tak mapu pro hledání
    return kolejiste_root, mapa_id

def vypis_prvku(hledane_id, registr):
    """Najde prvek a vypíše celý jeho podstrom (všechny úrovně pod ním)."""
    start_objekt = registr.get(hledane_id)

    if not start_objekt:
        print(f"❌ ID {hledane_id} nebylo v systému nalezeno.")
        return

    print(f"\n🔍 KOMPLETNÍ PRŮZKUM: {start_objekt.nazev} ({start_objekt.id})")
    print("=" * 60)

    def vypis_rekurzivne(prvek, uroven=0):
        odsazeni = "  " * uroven
        identifikace = f"{prvek.nazev} ({prvek.id})"

        if prvek.is_leaf:
            # Výpis koncového prvku s detaily
            print(
                f"{odsazeni}🔌 {identifikace:<25} | ADR: {prvek.adresa:<2} | PORT: {prvek.port:<2} | ALGO: {prvek.algoritmus}")
        else:
            # Výpis skupiny (Stanice / Budova)
            ikona = "📍" if uroven == 0 else "🏢"
            print(f"{odsazeni}{ikona} {identifikace} [SKUPINA]")

            # Tady je to kouzlo: funkce zavolá samu sebe pro každé dítě
            for dite in prvek.deti:
                vypis_rekurzivne(dite, uroven + 1)

    # Spustíme rekurzi od nalezeného prvku
    vypis_rekurzivne(start_objekt)
    print("=" * 60)

def vypis_strukturu(prvek, uroven=0):
    """Rekurzivně vypíše všechny prvky a okruhy v systému."""
    odsazeni = "  " * uroven

    # Příprava textu s názvem a ID
    # Používáme f-string pro spojení názvu a ID v závorce
    identifikace = f"{prvek.nazev} ({prvek.id})"

    if uroven == 0:
        print(f"🌐 {identifikace}")
    elif not prvek.is_leaf:
        # Stanice nebo Budova
        ikona = "📍" if uroven == 1 else "🏢"
        print(f"{odsazeni}{ikona} {identifikace}")
    else:
        # Koncový okruh (přidáno zarovnání pro ID v závorce)
        print(
            f"{odsazeni}  🔌 {identifikace:<28} | ADR: {prvek.adresa:<2} | PORT: {prvek.port:<2} | ALGO: {prvek.algoritmus}")

    # Rekurzivní volání pro všechny podřízené prvky
    for dite in prvek.deti:
        vypis_strukturu(dite, uroven + 1)

def vrat_cas(datum, oblast, data):
    tyden = datum.isocalendar()[1]
    print(f"Tyden: {tyden}")

    with open(data, 'r', encoding='utf-8') as f:
        data = json.load(f)

    vypnutiJ, zapnutiJ = data[str(tyden)][oblast]
    vypnuti = datetime.strptime(vypnutiJ, "%H:%M")
    zapnuti = datetime.strptime(zapnutiJ, "%H:%M")

    tz = zoneinfo.ZoneInfo("Europe/Prague")
    dt = datetime(datum.year, datum.month, datum.day, tzinfo=tz)

    if bool(dt.dst()): # řeší letní čas
        vypnuti += timedelta(hours=1)
        zapnuti += timedelta(hours=1)
    return vypnuti, zapnuti