import uvicorn
import threading

from mtb import DaemonClient, EDaemonResponse
from configurate import load_configuration, ConfigManager
from web import app

sunrise, sunset, config_file = load_configuration()
print(f"Východ: {sunrise}")

# 1. Vytvoření jediné hlavní instance správce konfigurace přímo v main.py
manager = ConfigManager()


def ovladani_konzole():
    while True:
        prikaz = input()
        if prikaz.strip().lower() == 'p':
            print("\n=== Aktuální struktura kolejiště ===")

            # Konzole používá naši hlavní instanci manager z tohoto souboru
            manager.print_structure()
            print("====================================\n")


def udrzuj_demona(daemon):
    try:
        daemon.keep_alive()
    except Exception as e:
        print(f"Spojení s démonem bylo přerušeno: {e}")


def main() -> None:
    global daemon
    tree, flat_list = manager.load_yaml('configurate/railway00.yaml')

    # Předání sdílených dat webové aplikaci
    app.state.manager = manager
    app.state.sunrise = str(sunrise)
    app.state.sunset = str(sunset)

    try:
        daemon = DaemonClient()
        app.state.daemon = daemon

        print("Démon připojen. Odesílám počáteční stavy světel...")
        # Úvodní nastavení hardwaru hned po startu
        manager.update_hardware(daemon, str(sunrise), str(sunset))

        daemon_vlakno = threading.Thread(target=udrzuj_demona, args=(daemon,), daemon=True)
        daemon_vlakno.start()

        # Vlákno smycka_osvetleni zatím spouštět nemusíme,
        # protože teď reagujeme jen na okamžité změny z webu.

    except EDaemonResponse as e:
        print(f"Chyba při komunikaci s démonem: {e}")
    except ConnectionRefusedError:
        print("Nepodařilo se připojit k MTB démonovi. Běží na portu 3841?")

    konzole_vlakno = threading.Thread(target=ovladani_konzole, daemon=True)
    konzole_vlakno.start()

    print("Startuji webový server na http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == '__main__':
    main()