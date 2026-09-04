"""Debt schedule from IFRS note 21 (YE2025, thousands->bn) + H1 2026 update.
Buckets only (coupons per issue undisclosed -> blended cod + flagged gap).
Saves magnit/data/debt_schedule.json
"""
import json, pathlib

SCHED = {
    "as_of": "2025-12-31",
    "long": [
        {"kind": "bank", "maturity": "2027-2028", "amount": 289.4, "prev": 78.6, "prev_mat": "2026-2028"},
        {"kind": "bonds", "maturity": "2027-2034", "amount": 180.6, "prev": 74.1, "prev_mat": "2026-2029"},
        {"kind": "current_portion", "maturity": "<1y", "amount": -2.2, "prev": -1.7, "prev_mat": ""},
    ],
    "long_total": 467.8,
    "short": [
        {"kind": "bonds", "maturity": "2026", "amount": 198.6, "prev": 20.1, "prev_mat": "2025"},
        {"kind": "bank", "maturity": "2026", "amount": 74.1, "prev": 233.5, "prev_mat": "2025"},
        {"kind": "repo", "maturity": "2026", "amount": 3.0, "prev": 5.5, "prev_mat": "2025"},
        {"kind": "current_portion_lt", "maturity": "2026", "amount": 2.2, "prev": 1.7, "prev_mat": "2025"},
    ],
    "short_total": 277.9,
    "h1_2026": {"long": 658.9, "short": 263.3, "cash": 404.1,
                "note": "H1 balance-sheet note; instrument split H1 undisclosed"},
    "gaps": ["per-issue coupons undisclosed -> blended cod 17.1/16.0 used",
             "fixed/floating mix undisclosed", "bank facility terms/undrawn pricing undisclosed"],
    "source": "IFRS FY2025 note 21 (primary); H1 2026 balance sheet",
}
tot = round(sum(r["amount"] for r in SCHED["long"]) + sum(r["amount"] for r in SCHED["short"]), 1)
assert abs(tot - (467.8 + 277.9)) < 0.2, tot
# bucketed wall (maturity ranges as stated)
wall = {}
for r in SCHED["long"] + SCHED["short"]:
    if r["amount"] <= 0: continue
    wall[r["maturity"]] = round(wall.get(r["maturity"], 0) + r["amount"], 1)
SCHED["wall_bn"] = wall
pathlib.Path("magnit/data/debt_schedule.json").write_text(json.dumps(SCHED, ensure_ascii=False, indent=1), encoding="utf-8")
print("wall:", wall, "| total:", tot)
print("saved debt_schedule.json")
