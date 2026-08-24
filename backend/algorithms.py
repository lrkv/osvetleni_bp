from datetime import datetime, timedelta

def parse_time_to_datetime(time_str: str, current_date: datetime.date) -> datetime:
    """
    Pomocná funkce, která vezme text (např. '5:32') a dnešní datum,
    a vytvoří z nich plnohodnotný časový údaj pro matematické operace.
    """
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])

    return datetime(
        year=current_date.year,
        month=current_date.month,
        day=current_date.day,
        hour=hours,
        minute=minutes
    )

def evaluate_algorithm(algorithm_name: str, sunrise_str: str = "00:00", sunset_str: str = "00:00") -> int:
    """
    Vyhodnotí algoritmus a vrátí hodnotu pro MTB démona:
    1 = zapnuto
    0 = vypnuto
    60 = blikání (kmitání)
    """

    # --- 1. Statické stavy ---
    if algorithm_name == "trvale_zapnuto":
        return 1

    elif algorithm_name == "trvale_vypnuto":
        return 0

    elif algorithm_name == "disco":
        return 60

    # --- 2. Dynamické časové stavy ---
    elif algorithm_name == "poulicni_lampa":
        now = datetime.now()
        today = now.date()

        sunrise_dt = parse_time_to_datetime(sunrise_str, today)
        sunset_dt = parse_time_to_datetime(sunset_str, today)

        lights_off_time = sunrise_dt + timedelta(hours=1)
        lights_on_time = sunset_dt - timedelta(hours=1)

        if now >= lights_on_time or now <= lights_off_time:
            return 1
        else:
            return 0

    # --- 3. Simulace domácnosti (sudá/lichá minuta) ---
    elif algorithm_name == "domacnost":
        now = datetime.now()

        # Zjištění, zda je aktuální minuta sudá
        if now.minute % 2 == 0:
            return 1  # Sudá minuta -> svítí
        else:
            return 0  # Lichá minuta -> nesvítí

    # Výchozí ochrana pro neznámé algoritmy
    return 0