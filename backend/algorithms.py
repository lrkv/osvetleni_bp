def evaluate_algorithm(algorithm_name: str, sunrise_str: str = "00:00", sunset_str: str = "00:00") -> int:
    """
    Vyhodnotí algoritmus a vrátí hodnotu pro MTB démona:
    1 = trvale zapnuto
    0 = trvale vypnuto
    60 = blikání (kmitání)
    """

    if algorithm_name == "trvale_zapnuto":
        return 1

    elif algorithm_name == "trvale_vypnuto":
        return 0

    elif algorithm_name == "disco":
        return 60

    # Ostatní složitější algoritmy (domacnost, poulicni_lampa, drazni_osvetleni) vyřešíme pak.
    # Zatím je necháme jako vypnuté.
    return 0