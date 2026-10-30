"""Read-only preview of scheduled changes; never draws random numbers or advances timers."""
from datetime import timedelta
from time import monotonic
import math

from algorithms import evaluate_algorithm, parse_time_to_datetime


def fixed_changes(algorithm, now, sunrise, sunset):
    if algorithm == "minuta":
        first = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        return [(at, bool(at.minute % 2)) for at in (first, first + timedelta(minutes=1))]
    candidates = set()
    for day in range(-1, 3):
        date = (now + timedelta(days=day)).date()
        rise = parse_time_to_datetime(sunrise, date)
        setting = parse_time_to_datetime(sunset, date)
        midnight = rise.replace(hour=0, minute=0, second=0, microsecond=0)
        if algorithm == "prodejna":
            candidates.update((midnight + timedelta(hours=7), midnight + timedelta(hours=19)))
        elif algorithm == "poulicni_lampa":
            candidates.update((midnight, rise + timedelta(hours=1, seconds=1), setting - timedelta(hours=1)))
        elif algorithm == "drazni_osvetleni":
            candidates.update((rise - timedelta(minutes=15), setting + timedelta(minutes=15)))
    changes = []
    for at in sorted(candidates):
        if not now < at <= now + timedelta(days=1):
            continue
        before = evaluate_algorithm(algorithm, sunrise, sunset, now=at - timedelta(seconds=1))
        after = evaluate_algorithm(algorithm, sunrise, sunset, now=at)
        if before != after:
            changes.append((at, bool(after)))
    return changes


def upcoming_events(manager, sunrise, sunset, now, status, real_now):
    elapsed = monotonic()
    speed = status.get("speed", 1) if status.get("running") and status.get("available") else 0
    source = "model" if status.get("source") == "hjop" else "real"
    rows = []
    unknown = []
    fixed = {}
    paths = {}

    def walk(nodes, parents=()):
        for node in nodes:
            paths[node["id"]] = " / ".join(parents)
            walk(node.get("items", []), (*parents, node.get("name", "")))
    walk(manager.tree_data.get("groups", []))

    def add(item, on, seconds, at, basis, kind="scheduled"):
        anchor = now if basis == "model" else real_now
        model_at = (at if basis == "model" else
                    now + timedelta(seconds=seconds * speed) if source == "model" and now is not None and speed > 0 and seconds is not None else None)
        rows.append({"id": item["id"], "name": item.get("name", ""),
                     "path": paths.get(item["id"], ""), "address": item["address"],
                     "algorithm": item.get("algorithm"), "on": on, "kind": kind,
                     "seconds": math.ceil(max(0, seconds)) if seconds is not None else None,
                     "time": at.strftime("%H:%M:%S"), "day_offset": (at.date() - anchor.date()).days,
                     "basis": basis, "at_key": at.isoformat(timespec="seconds"),
                     "model_time": model_at.strftime("%H:%M:%S") if model_at else None,
                     "model_day_offset": (model_at.date() - now.date()).days if model_at else None})

    for item in manager.items_by_id.values():
        if "address" not in item or item.get("configuration_error"):
            continue
        algorithm = item.get("algorithm")
        if algorithm in ("prodejna", "poulicni_lampa", "drazni_osvetleni", "minuta"):
            if now is None:
                unknown.append({"id": item["id"], "name": item.get("name"), "reason": "Čeká na čas hJOP"})
                continue
            if algorithm not in fixed:
                fixed[algorithm] = fixed_changes(algorithm, now, sunrise, sunset)
            for at, on in fixed[algorithm]:
                seconds = (at - now).total_seconds() / speed if speed > 0 else None
                add(item, on, seconds, at, source)
        elif algorithm == "chodba":
            corridor = manager._corridors.get(item["id"])
            if corridor is None or corridor.deadline is None or now is None:
                unknown.append({"id": item["id"], "name": item.get("name"), "reason": "Další rozsvícení se losuje během noci"})
                continue
            seconds = max(0, corridor.deadline - elapsed)
            # The end of the night cancels a pending turn-on or turns an active light off earlier.
            dawn = parse_time_to_datetime(sunrise, now.date())
            if dawn <= now:
                dawn += timedelta(days=1)
            until_dawn = (dawn - now).total_seconds() / speed if speed > 0 else math.inf
            if until_dawn <= seconds:
                if corridor.is_on:
                    add(item, False, until_dawn, dawn, source)
                else:
                    unknown.append({"id": item["id"], "name": item.get("name"), "reason": "Pauza končí až po východu slunce"})
            else:
                add(item, not corridor.is_on, seconds, real_now + timedelta(seconds=seconds), "real")
        elif algorithm == "domacnost":
            state = manager._households._states.get(item["id"])
            if state is not None and state.deadline is not None:
                seconds = max(0, state.deadline - elapsed)
                add(item, False, seconds, real_now + timedelta(seconds=seconds), "real", "latest")
            else:
                unknown.append({"id": item["id"], "name": item.get("name"), "reason": "Rozsvícení závisí na podílu domácností a náhodném výběru"})
    rows.sort(key=lambda row: (row["seconds"] is None, row["seconds"] if row["seconds"] is not None else math.inf,
                               row["day_offset"], row["time"], row["id"]))
    return {"events": rows, "unknown": unknown, "model_paused": source == "model" and speed <= 0}
