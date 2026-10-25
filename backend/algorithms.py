import random
from datetime import datetime, timedelta
from time import monotonic


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


class CorridorLighting:
    """One independent schedule per light; deadlines use a monotonic clock."""
    def __init__(self, pause_min_seconds=60, pause_max_seconds=300):
        if not 0 < pause_min_seconds <= pause_max_seconds:
            raise ValueError("Pauzy chodby musí být kladné a minimum nesmí překročit maximum.")
        self.pause_min_seconds = pause_min_seconds
        self.pause_max_seconds = pause_max_seconds
        self.night_start = None
        self.is_on = False
        self.deadline = None

    def evaluate(self, now, sunrise_str, sunset_str):
        sunset = parse_time_to_datetime(sunset_str, now.date())
        sunrise = parse_time_to_datetime(sunrise_str, now.date())
        if sunrise <= sunset:
            sunrise += timedelta(days=1)
        night_start = None
        for days_ago in (0, 1):
            shift = timedelta(days=days_ago)
            if sunset - shift <= now < sunrise - shift:
                night_start = sunset - shift
                break

        if night_start is None:
            self.night_start = None
            self.is_on = False
            self.deadline = None
            return 0

        elapsed = monotonic()
        if self.night_start != night_start:
            self.night_start = night_start
            self.is_on = False
            self.deadline = elapsed + random.randint(self.pause_min_seconds, self.pause_max_seconds)
        elif elapsed >= self.deadline:
            self.is_on = not self.is_on
            duration = (random.randint(20, 30) if self.is_on else
                        random.randint(self.pause_min_seconds, self.pause_max_seconds))
            self.deadline = elapsed + duration
        return int(self.is_on)


def evaluate_algorithm(algorithm_name: str, sunrise_str: str = "00:00", sunset_str: str = "00:00", *, corridor: CorridorLighting | None = None, now: datetime | None = None) -> int:
    """
    Vyhodnotí algoritmus a vrátí hodnotu pro MTB démona:
    1 = zapnuto
    0 = vypnuto
    60 = blikání (kmitání)
    """

    # --- 1. Statické stavy ---
    if algorithm_name in ("trvale_zapnuto", "vyloha"):
        return 1

    elif algorithm_name == "trvale_vypnuto":
        return 0

    elif algorithm_name == "disco":
        return 60

    elif algorithm_name == "chodba":
        if corridor is None:
            raise ValueError("Algoritmus chodba potřebuje vlastní instanci CorridorLighting.")
        return corridor.evaluate(now if now is not None else datetime.now(), sunrise_str, sunset_str)

    elif algorithm_name == "prodejna":
        now = now if now is not None else datetime.now()
        return int(7 <= now.hour < 19)

    elif algorithm_name == "byt":
        now = now if now is not None else datetime.now()
        sunrise = parse_time_to_datetime(sunrise_str, now.date())
        sunset = parse_time_to_datetime(sunset_str, now.date())
        morning_start = now.replace(hour=5, minute=0, second=0, microsecond=0)
        evening_end = now.replace(hour=21, minute=0, second=0, microsecond=0)
        return int(morning_start <= now < sunrise or sunset <= now < evening_end)

    # --- 2. Dynamické časové stavy ---
    elif algorithm_name == "poulicni_lampa":
        now = now if now is not None else datetime.now()
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
        now = now if now is not None else datetime.now()

        # Zjištění, zda je aktuální minuta sudá
        if now.minute % 2 == 0:
            return 1  # Sudá minuta -> svítí
        else:
            return 0  # Lichá minuta -> nesvítí

    elif algorithm_name == "drazni_osvetleni":
        now = now if now is not None else datetime.now()
        sunset_dt = parse_time_to_datetime(sunset_str, now.date())
        sunrise_dt = parse_time_to_datetime(sunrise_str, now.date())
        if sunrise_dt <= sunset_dt:
            sunrise_dt += timedelta(days=1)

        lights_on_time = sunset_dt + timedelta(minutes=15)
        lights_off_time = sunrise_dt - timedelta(minutes=15)
        # Check the nights starting today and yesterday. Offsets may cross midnight.
        for days_ago in (0, 1):
            shift = timedelta(days=days_ago)
            if lights_on_time - shift <= now < lights_off_time - shift:
                return 1
        return 0

    # Výchozí ochrana pro neznámé algoritmy
    else:
        print(f"Algoritmus: {algorithm_name} není implementovaný.")
    return 0