from datetime import datetime


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


