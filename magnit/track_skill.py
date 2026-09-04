"""LFL nowcast backtest: QUARTERLY ONLY, expanding window, point-in-time.
Target = Magnit quarterly LFL yoy (same variable as the live nowcast).
Proxy = 0.4*food_q + 0.6*x5 (X5 LFL where available 2024Q2+, else X5 total flagged)
  + trailing gap (expanding mean of prior gaps, never the current origin).
No H1/9M/FY mixing, no overlapping windows. Reports MAE, direction hit-rate,
and interval coverage (share of actuals inside ±MAE band).
Saves magnit/data/skill_lfl.json (live nowcast reads its MAE as interval).
"""
import json, pathlib, statistics

DATA = pathlib.Path(__file__).parent / "data"
food_q = json.loads((DATA / "macro" / "food_monthly.json").read_text(encoding="utf-8"))["quarterly_food_cumul_pct"]
x5 = json.loads((DATA / "peers" / "x5_quarterly.json").read_text(encoding="utf-8"))["quarters"]
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))

MG = {(x["period"]): x["value"] for x in reg
      if x["series"] == "lfl" and x["status"] == "ok" and len(x["period"]) == 6 and x["period"][4] == "Q"}
# len 6 + Q at idx4 -> 'YYYYQN' quarterly only (excludes H1/9M/FY)
OLD = json.loads((DATA / "peers" / "x5_quarterly.json").read_text(encoding="utf-8")).get("x5_old_perimeter_mln", {})


def x5_base(qk):
    y = int(qk[:4])
    return OLD.get(f"{y-1}{qk[4:]}")


def x5_proxy(q):
    if q in x5 and x5[q].get("x5_lfl") is not None:
        return x5[q]["x5_lfl"], "lfl"
    y = int(q[:4])
    cur = x5.get(q, {}).get("revenue_mln") or OLD.get(q)
    base = x5.get(f"{y-1}{q[4:]}", {}).get("revenue_mln") or x5_base(q)
    if cur and base:
        return round((cur / base - 1) * 100, 1), "total-flagged"
    return None, "missing"


def food_of(q):
    return food_q.get(f"{q[:4]}-Q{q[5]}")


rows, gaps = [], []
for period in sorted(MG):
    act = MG[period]
    food = food_of(period)
    xo, kind = x5_proxy(period)
    if food is None or xo is None:
        continue
    market = 0.4 * food + 0.6 * xo
    gap = sum(gaps) / len(gaps) if gaps else 0.0
    pred = market + gap
    rows.append({"period": period, "act": act, "food": food, "x5": xo, "x5_kind": kind,
                 "market": round(market, 2), "gap_used": round(gap, 2),
                 "pred": round(pred, 2), "err": round(pred - act, 2)})
    gaps.append(act - market)

errs = [abs(r["err"]) for r in rows]
mae = round(statistics.mean(errs), 2)
dirs = sum(1 for i in range(1, len(rows))
           if ((rows[i]["pred"] - rows[i - 1]["act"]) < 0) == ((rows[i]["act"] - rows[i - 1]["act"]) < 0))
cover = round(sum(1 for r in rows if abs(r["err"]) <= mae) / len(rows), 3) if rows else 0
print(f"{'period':<9} {'act':>6} {'food':>6} {'x5':>6} {'kind':>13} {'pred':>6} {'err':>6}")
for r in rows:
    print(f"{r['period']:<9} {r['act']:>5.1f}% {r['food']:>5.2f}% {r['x5']:>5.1f}% {r['x5_kind']:>13} {r['pred']:>5.2f}% {r['err']:>+5.2f}")
print(f"\nn={len(rows)} MAE {mae}pp direction {dirs}/{len(rows)-1} interval-coverage {cover:.0%}")
json.dump({"origins": rows, "mae_pp": mae, "direction": f"{dirs}/{len(rows)-1}",
           "final_gap": round(gaps[-1], 2) if gaps else 0.0,
           "interval_coverage": cover, "bridge": "LFL = 0.4*food_q + 0.6*x5 + expanding-mean gap",
           "design": "quarterly-only, no overlaps, point-in-time proxies (X5 total pre-2024Q2 flagged)",
           "caveats": ["direction ~ coin flip: level skill only, no turning-point skill",
                       "pre-2024Q2 X5 proxy is total revenue (own expansion inside)"]},
          open(DATA / "skill_lfl.json", "w"), ensure_ascii=False, indent=1)
print("saved skill_lfl.json")
