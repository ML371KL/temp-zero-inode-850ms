"""Point-in-time query helper: rows visible as of a knowledge date.
Rule: latest non-superseded vintage with avail_since <= date.
avail_since = released_at (same-day availability assumption, stated; a +1d-lag
variant is strictly more conservative and changes only boundary origins).
first_seen is OUR fetch audit trail (different concept, kept separately).
"""
from __future__ import annotations
import json


def rows_as_of(registry: list, date: str, status_ok_only: bool = True) -> list:
    best = {}
    for x in sorted(registry, key=lambda z: (z.get("avail_since", ""), z.get("vintage_id", ""))):
        if x.get("avail_since", "") > date:
            continue
        if x.get("status") == "superseded":
            continue
        if status_ok_only and x.get("status") != "ok":
            continue
        best[(x["series"], x["period"], x.get("basis", ""))] = x
    return sorted(best.values(), key=lambda z: (z["as_of"], z["series"]))


if __name__ == "__main__":
    import pathlib
    reg = json.loads(pathlib.Path("magnit/data/registry.json").read_text(encoding="utf-8"))
    for d in ("2024-05-01", "2025-05-01", "2026-09-04"):
        rows = rows_as_of(reg, d)
        nq = sum(1 for x in rows if x["status"] == "quarantine")
        print(d, "visible rows:", len(rows), f"(quarantine {nq} excluded)")
