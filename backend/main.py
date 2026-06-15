from asyncio.windows_events import NULL
from time import sleep

import yaml
import json
import zoneinfo
import time
import threading
import time
import logging
from flask import Flask
from datetime import datetime, timedelta, date
from nastroje import nacti_strukturu, vypis_prvku, vypis_strukturu, vrat_cas

zdroj = 'data.yaml'
osvetlovaciKalendar = 'osvetlovaciKalendar.json'
kolejiste = None
registr = None

app = Flask(__name__)

@app.route('/')
def home():
    return f"Web běží! \n {osvetlovaciKalendar} xD"

def smycka_na_pozadi():
    posledniCas = None
    while True:
        aktualniCas = datetime.now().strftime("%H:%M")
        sleep(10)

        if aktualniCas != posledniCas:
            posledniCas = aktualniCas
            print(f"AktualniCas: {aktualniCas}")

def main():
    global kolejiste, registr
    kolejiste, registr = nacti_strukturu(zdroj)
    print("Spouštím systém...")
    vlakno_smycka = threading.Thread(target=smycka_na_pozadi, daemon=True)
    vlakno_konzole = threading.Thread(target=konzole_uzivatele, daemon=True)
    vlakno_konzole.start()
    vlakno_smycka.start()
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    app.run(host='0.0.0.0', port=5000)

def konzole_uzivatele():
    while True:
        prikaz = input("Zadej příkaz (nebo 'konec'): \n")

        if prikaz == "konec":
            print("[Konzole] Tento příkaz by mohl něco vypnout...")
        elif prikaz == "vypis":
            vypis_strukturu(kolejiste)
        elif prikaz == "prvek":
            vypis_prvku(int(input("Zadej číslo: ")), registr)
        elif prikaz != "":
            print(f"[Konzole] Zadal jsi příkaz: {prikaz}")

if __name__ == "__main__":
    main()

    """

    vypis_strukturu(kolejiste)


    datum = date.today()
    #datum = date(2025, 7, 25)

    vypnuti, zapnuti = vrat_cas(datum, "II", osvetlovaciKalendar)
    print(f"Zapnuti: {zapnuti}, Vypnuti: {vypnuti}")

    vypis_prvku(10, registr)

 """
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
