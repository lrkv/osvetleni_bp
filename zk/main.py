#!/usr/bin/env python3

import socket
from typing import Dict, Any
import json
import yaml

from zk.struktura import Skupina, najdi_prvek_podle_id, ziskej_id_svetelnych_okruhu

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


class EDaemonResponse(Exception):
    pass


def request_response(socket: socket.socket, request: Dict[str, Any]) -> Dict[str, Any]:
    to_send = request
    to_send['type'] = 'request'
    socket.send((json.dumps(to_send)+'\n').encode('utf-8'))

    while True:
        data = socket.recv(0xFFFF).decode('utf-8').strip()
        messages = [json.loads(msg) for msg in data.split('\n')]
        for message in messages:
            assert isinstance(message, dict)
            if message.get('command', '') == request['command']:
                if message.get('status', '') != 'ok':
                    raise EDaemonResponse(
                        message.get('error', {}).get('message', 'Unknown error!')
                    )
                return message

# funkce která zapne / vypne osvětlení
def change(module, port, value):
    global sock

    ports = port if isinstance(port, list) else [port]

    request_response(sock, {
        'command': 'module_set_outputs',
        'address': module,
        'outputs': {p: {'type': 'plain', 'value': value} for p in ports},
    })

soubor_s_daty = "data.yaml"

def main() -> None:
    # připojení k HW
    global sock
    sock.connect(('127.0.0.1', 3841))

    # načtení struktury
    with open(soubor_s_daty, 'r', encoding='utf-8') as soubor:
        data = yaml.safe_load(soubor)

    moje_kolejiste = Skupina(data)
    moje_kolejiste.vypis()

    # Hlavní smyčka v main()
    while True:
        sock.recv(0xFFFF).decode('utf-8').strip()

        vstup = input("\nZadej ID (nebo 'q' pro konec): ")
        if vstup.lower() in ['q', 'konec', 'exit', 'quit']:
            print("Ukončuji program...")
            break

        try:
            testovaci_id = int(vstup)
        except ValueError:
            print("❌ CHYBA: Zadej platné celé číslo!")
            continue

        vstup2 = input("Zadej stav (1 = zapnout, 0 = vypnout): ")
        if vstup2 == "1":
            stav = 1
        else:
            stav = 0

        # 3. Získání ID VŠECH světelných okruhů pod zadaným ID
        id_okruhu = ziskej_id_svetelnych_okruhu(moje_kolejiste, testovaci_id)

        if not id_okruhu:
            print("⚠️ Prvek neexistuje, nebo pod ním nejsou žádná světla.")
            continue

        # print(f"✅ Nalezena světla s ID: {id_okruhu}")

        # 4. Cyklus přes všechny okruhy a volání funkce change()
        for id_svetla in id_okruhu:
            # Najdeme konkrétní objekt světla, abychom z něj vyčetli modul a port
            svetlo = najdi_prvek_podle_id(moje_kolejiste, id_svetla)

            # Zavoláme tvoji funkci change
            change(svetlo.modul, svetlo.port, stav)


if __name__ == '__main__':
    main()