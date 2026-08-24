import uvicorn
import threading
import time

from mtb import DaemonClient, EDaemonResponse
from layout import load_configuration, ConfigManager
from web import app

sunrise, sunset, config_file = load_configuration()

# 1. Vytvoření jediné hlavní instance správce konfigurace přímo v main.py
manager = ConfigManager()

def console_control():
    while True:
        command = input()
        if command.strip().lower() == 'p':
            print("\n=== Current track structure ===")
            manager.print_structure()
            print("====================================\n")

def keep_daemon_alive(daemon):
    try:
        daemon.keep_alive()
    except Exception as e:
        print(f"Spojení s démonem bylo přerušeno: {e}")

def lighting_loop(client_daemon, sunrise_val, sunset_val):
    """Pravidelně přepočítává algoritmy závislé na čase (každou 1 vteřinu)."""
    while True:
        try:
            # Přepočítá stavy a rovnou updatuje i proměnnou is_on v paměti
            manager.update_hardware(client_daemon, sunrise_val, sunset_val)
        except Exception:
            pass
        time.sleep(1)

def main() -> None:
    global daemon
    tree, flat_list = manager.load_yaml('configurate/lrkv_tt.yaml')

    # Předání sdílených dat webové aplikaci
    app.state.manager = manager
    app.state.sunrise = str(sunrise)
    app.state.sunset = str(sunset)

    # Přednastavíme démona na None pro případ, že by se připojení nezdařilo
    daemon = None
    app.state.daemon = None

    try:
        daemon = DaemonClient()
        app.state.daemon = daemon

        daemon_thread = threading.Thread(target=keep_daemon_alive, args=(daemon,), daemon=True)
        daemon_thread.start()
        print("MTB Démon úspěšně připojen.")

    except EDaemonResponse as e:
        print(f"Chyba při komunikaci s démonem: {e}")
    except ConnectionRefusedError:
        print("Nepodařilo se připojit k MTB démonovi. Běží na portu 3841? (Běžím v režimu bez hardwaru)")
    except Exception as e:
        print(f"Neočekávaná chyba při připojování k démonovi: {e}")

    # TOTO MUSÍ PROBĚHNOUT VŽDY - i když daemon = None
    # Zajistí to počáteční výpočet stavu 'is_on' a okamžité obarvení zapnutých prvků na webu.
    manager.update_hardware(daemon, str(sunrise), str(sunset))

    # Tímto se spustí ta nová pravidelná kontrola pro domácnosti a pouliční lampy
    lighting_thread = threading.Thread(target=lighting_loop, args=(daemon, str(sunrise), str(sunset)), daemon=True)
    lighting_thread.start()

    console_thread = threading.Thread(target=console_control, daemon=True)
    console_thread.start()

    print("Startuji webový server na http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == '__main__':
    main()