from time import sleep

import yaml
import json
import zoneinfo
import time
from datetime import datetime, timedelta, date
from nastroje import nacti_strukturu, vypis_prvku, vypis_strukturu, vrat_cas

zdroj = 'data.yaml'
osvetlovaciKalendar = 'osvetlovaciKalendar.json'

if __name__ == "__main__":

    kolejiste, registr = nacti_strukturu(zdroj)

    vypis_strukturu(kolejiste)


    datum = date.today()
    #datum = date(2025, 7, 25)

    vypnuti, zapnuti = vrat_cas(datum, "II", osvetlovaciKalendar)
    print(f"Zapnuti: {zapnuti}, Vypnuti: {vypnuti}")

    vypis_prvku(10, registr)

    posledniCas = None

    while True:
        aktualniCas = datetime.now().strftime("%H:%M")
        sleep()

        if aktualniCas != posledniCas:
            posledniCas = aktualniCas
            print(f"AktualniCas: {aktualniCas}")

    """
    print("💡 Tip: Pro ukončení napiš 'exit' nebo 'q'.")
    while (vstup := input("\nZadej ID k nalezení: ")).lower() not in ["exit", "q"]:
        try:
            id_cislo = int(vstup)
            vypis_prvku(id_cislo, registr)
        except ValueError:
            print("⚠️  Chyba: Zadej platné číslo ID nebo příkaz 'exit'.")

    print("👋 Systém ukončen. Šťastnou cestu!")
    """
