"""Nowcast skill tracker (v1 bridge) on quarterly origins with REAL proxies.
Bridge: pred = 0.4*food + 0.6*x5 + trailing_gap (point-in-time).
Benchmarks: naive_x5 (X5 print), naive_trail (Magnit trailing same-length).
Food/X5 aggregated to origin length by chaining (food) / level sums (X5).
Saves magnit/data/skill_v1.json
"""
import json, pathlib

DATA = pathlib.Path(__file__).parent / "data"
food_q = json.loads((DATA / "macro" / "food_monthly.json").read_text(encoding="utf-8"))["quarterly_food_cumul_pct"]
x5 = json.loads((DATA / "peers" / "x5_quarterly.json").read_text(encoding="utf-8"))["quarters"]
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))

# Magnit reported revenue_yoy by period (primary)
MG = {x["period"]: x["value"] for x in reg if x["series"] == "revenue_yoy" and x["status"] == "ok"}
# X5 2021 base for 2022 yoy (old book, mln)
X5_2021 = {"2021Q1": 507191, "2021Q2": 546512, "2021Q3": 543586, "2021Q4": 607530}
X5_2022 = {"2022Q1": 604230, "2022Q2": 647950, "2022Q3": 647869, "2022Q4": 705183}

def x5_base(qk):
    y = int(qk[:4])
    pq = f"{y-1}{qk[4:]}"
    if pq in x5: return x5[pq]["revenue_mln"]
    return X5_2022.get(pq, X5_2021.get(pq))
x5yoy = {}
for q in ("2022Q1", "2022Q2", "2022Q3", "2022Q4"):
    x5yoy[q] = round((X5_2022[q] / X5_2021[q.replace("2022", "2021")] - 1) * 100, 1)

def chain_food(qlist):
    p = 1.0
    for q in qlist: p *= (1 + food_q[q] / 100)
    return round((p - 1) * 100, 2)

def x5_level_sum(qlist):
    s, b = 0, 0
    for q in qlist:
        qk = q.replace("-", "")  # 2022-Q1 -> 2022Q1
        cur = x5[qk]["revenue_mln"] if qk in x5 else X5_2022.get(qk)
        base = x5_base(qk)
        assert cur and base, qk
        s += cur; b += base
    return round((s / b - 1) * 100, 1)

ORIGINS = [  # (magnit period, quarter list, label)
    ("2022Q1", ["2022-Q1"]), ("2022Q2", ["2022-Q2"]), ("2022H1", ["2022-Q1", "2022-Q2"]),
    ("2022FY", ["2022-Q1", "2022-Q2", "2022-Q3", "2022-Q4"]),
    ("2023Q1", ["2023-Q1"]), ("2023Q2", ["2023-Q2"]), ("2023H1", ["2023-Q1", "2023-Q2"]),
    ("2023Q3", ["2023-Q3"]), ("2023-9M", ["2023-Q1", "2023-Q2", "2023-Q3"]),
    ("2023FY", ["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4"]),
    ("2024H1", ["2024-Q1", "2024-Q2"]), ("2024FY", ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"]),
    ("2025H1", ["2025-Q1", "2025-Q2"]), ("2025FY", ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]),
    ("2026H1", ["2026-Q1", "2026-Q2"]),
]
A, B = 0.4, 0.6
rows, prev_gap, prev_act = [], None, None
for period, ql in ORIGINS:
    if period not in MG: continue
    act = MG[period]
    food = chain_food(ql)
    qks = [q.replace("-", "") for q in ql]
    if len(qks) == 1 and qks[0] in x5 and x5[qks[0]].get("revenue_yoy"):
        xv = x5[qks[0]]["revenue_yoy"]
    elif len(qks) == 1 and qks[0] in x5yoy:
        xv = x5yoy[qks[0]]
    else:
        xv = x5_level_sum(ql)
    market = A * food + B * xv
    spread = 0.0 if prev_gap is None else prev_gap
    pred = market + spread
    rows.append({"period": period, "act": act, "food": food, "x5": xv,
                 "market": round(market, 2), "spread": round(spread, 2),
                 "pred": round(pred, 2), "err": round(pred - act, 2),
                 "naive_x5_err": round(xv - act, 2)})
    prev_gap = act - market
    prev_act = act

import statistics
errs = [abs(r["err"]) for r in rows]
nx = [abs(r["naive_x5_err"]) for r in rows]
dirs = sum(1 for i in range(1, len(rows)) if ((rows[i]["pred"] - rows[i-1]["act"]) < 0) == ((rows[i]["act"] - rows[i-1]["act"]) < 0))
print(f"{'period':<9} {'act':>6} {'food':>6} {'x5':>6} {'pred':>6} {'err':>6} {'nx5err':>6}")
for r in rows:
    print(f"{r['period']:<9} {r['act']:>5.1f}% {r['food']:>5.2f}% {r['x5']:>5.1f}% {r['pred']:>5.2f}% {r['err']:>+5.2f} {r['naive_x5_err']:>+5.2f}")
print(f"\nn={len(rows)} bridge MAE {statistics.mean(errs):.2f}pp bias {statistics.mean([r['err'] for r in rows]):+.2f}pp "
      f"direction {dirs}/{len(rows)-1} | naive-X5 MAE {statistics.mean(nx):.2f}pp")
json.dump({"origins": rows,
           "mae_pp": round(statistics.mean(errs), 2),
           "bias_pp": round(statistics.mean([r["err"] for r in rows]), 2),
           "direction": f"{dirs}/{len(rows)-1}",
           "naive_x5_mae_pp": round(statistics.mean(nx), 2),
           "bridge": "rev = 0.4*food + 0.6*x5 + trailing_gap",
           "caveats": ["X5 assumed released before Magnit (verified 2-6wk lead on 4 recent cases only)",
                       "2022 bridge misses Dixy level shift (spread adapts with 1-period lag)"]},
          open(DATA / "skill_v1.json", "w"), ensure_ascii=False, indent=1)
print("saved skill_v1.json")
