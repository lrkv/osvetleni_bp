import random
import csv

# Názvy souborů (upravte podle potřeby)
vstupni_soubor = 'input.txt'
vystupni_soubor = 'vystup.csv'

try:
    # Načtení vět ze vstupního souboru
    with open(vstupni_soubor, 'r', encoding='utf-8') as f:
        # Přečte všechny řádky, odstraní prázdné znaky na koncích a vynechá prázdné řádky
        vety = [radek.strip() for radek in f if radek.strip()]

    # Kontrola, zda je v souboru dostatek vět pro výběr
    if len(vety) < 10:
        print(f"Chyba: Soubor musí obsahovat alespoň 10 vět, ale obsahuje jen {len(vety)}.")
    else:
        # Vytvoření hlavičky sloupců: 'číslo', 'otázka1', ..., 'otázka10'
        hlavicka = ['číslo'] + [f'otázka{i}' for i in range(1, 11)]

        # Otevření výstupního souboru
        # 'utf-8-sig' zajistí, že Excel rozpozná kódování a české znaky (BOM)
        with open(vystupni_soubor, 'w', encoding='utf-8-sig', newline='') as f:
            # V českém Excelu se jako oddělovač v CSV standardně používá středník
            writer = csv.writer(f, delimiter=';')
            writer.writerow(hlavicka)

            # Generování 55 řádků
            for cislo_radku in range(1, 56):
                # Náhodný výběr 10 unikátních vět z načteného seznamu
                vybrane_vety = random.sample(vety, 10)

                # Sestavení dat pro aktuální řádek a jejich zápis
                radek = [cislo_radku] + vybrane_vety
                writer.writerow(radek)

        print(f"Hotovo! Bylo vygenerováno 55 řádků a uloženo do souboru '{vystupni_soubor}'.")

except FileNotFoundError:
    print(
        f"Chyba: Vstupní soubor '{vstupni_soubor}' nebyl nalezen. Ujistěte se, že je ve stejné složce jako tento skript.")