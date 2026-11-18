"""Read-only preview of scheduled changes; never draws random numbers or advances timers."""
from datetime import timedelta
from time import monotonic
import math



def fixed_changes(algorithm, now, sunrise, sunset):
    from configurate import ConfigManager, load_settings
    instance = ConfigManager.from_settings(load_settings()["light"]).algorithm_for({"id": 0, "algorithm": algorithm})
    return instance.fixed_changes(now, sunrise, sunset) if instance else []


def upcoming_events(manager, sunrise, sunset, now, status, real_now):
    elapsed = monotonic()
    speed = status.get("speed", 1) if status.get("running") and status.get("available") else 0
    source = "model" if status.get("source") == "hjop" else "real"
    rows = []
    unknown = []
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
        instance = manager.algorithm_for(item)
        if instance is None:
            continue
        changes, reason = instance.forecast(item["id"], now, sunrise, sunset,
                                            speed, source, real_now, elapsed)
        for change in changes:
            add(item, change.on, change.seconds, change.at, change.basis, change.kind)
        if reason:
            unknown.append({"id": item["id"], "name": item.get("name"), "reason": reason})
    rows.sort(key=lambda row: (row["seconds"] is None, row["seconds"] if row["seconds"] is not None else math.inf,
                               row["day_offset"], row["time"], row["id"]))
    return {"events": rows, "unknown": unknown, "model_paused": source == "model" and speed <= 0}
