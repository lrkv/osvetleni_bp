#!/usr/bin/env python3
# main.py

import socket
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import yaml

from mtb import *

# Pro FastAPI a propojení s api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import api

# Lokální pomocné proměnné, které pak nakopírujeme do app.state
sunrise, sunset = None, None


def configLoad():
    global sunrise, sunset
    with open("config.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

        sunrise_str = data["light"]["sunrise"]
        sunset_str = data["light"]["sunset"]

        sunrise = datetime.strptime(sunrise_str, '%H:%M').time()
        sunset = datetime.strptime(sunset_str, "%H:%M").time()


async def mtb_background_loop(app: FastAPI):
    print("[MTB] Spouštím pozadí pro komunikaci s daemonem...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)

    # Uložíme socket do stavu aplikace, aby na něj vidělo api.py
    app.state.sock = sock

    loop = asyncio.get_event_loop()
    await loop.sock_connect(sock, ('127.0.0.1', 3841))
    print("[MTB] Úspěšně připojeno k MTB daemonu.")

    request_response(sock, {
        'command': 'module_set_outputs',
        'address': 1,
        'outputs': {
            0: {'type': 'plain', 'value': 1},
        },
    })

    while True:
        try:
            data = await loop.sock_recv(sock, 0xFFFF)
            if data:
                data_decoded = data.decode('utf-8').strip()
        except Exception as e:
            print(f"[MTB Chyba] Problém ve smyčce na pozadí: {e}")

        await asyncio.sleep(0.5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Spouštím aplikaci a načítám konfiguraci...")
    configLoad()
    print(f"Východ slunce je v {sunrise} a západ slunce je v {sunset}")

    # Uložení časů do stavu aplikace pro api.py
    app.state.sunrise = sunrise
    app.state.sunset = sunset
    app.state.sock = None  # Výchozí hodnota, než se připojí smyčka

    # Předáme 'app' do smyčky na pozadí
    asyncio.create_task(mtb_background_loop(app))
    yield

    if app.state.sock:
        print("Zavírám socket k MTB daemonu...")
        app.state.sock.close()


# Inicializace FastAPI
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Propojení směrovače z api.py (Teď už to projde bez chyby!)
app.include_router(api.router)

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)