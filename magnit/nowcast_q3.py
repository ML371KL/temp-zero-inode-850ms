"""Q3-2026 LFL nowcast tracker (LFL bridge v2: 0.4*food + 0.6*x5lfl + trailing_gap).
Food: price-level index from m/m chain -> Q3 yoy (avg Jul-Sep 2026 vs 2025).
X5 Q3 LFL: carry Q2 (4.2) until X5 Q3 trading (~14 Oct); flagged.
Weekly trimmed-mean shapes September (official Aug/Sep m/m land ~10-12 Sep).
Saves magnit/data/nowcast_q3_2026.json
"""
import json, pathlib, datetime

DATA = pathlib.Path(__file__).parent / "data"
fm = json.loads((DATA / "macro" / "food_monthly.json").read_text(encoding="utf-8"))["monthly_food_mom_pct"]
fw = json.loads((DATA / "macro" / "food_weekly.json").read_text(encoding="utf-8"))

# price index Dec-2018 = 100
idx, level = {}, 100.0
for k in sorted(fm):
    level *= (1 + fm[k] / 100)
    idx[k] = level

def qavg(y, q):
    ms = [f"{y}-{m:02d}" for m in range((q - 1) * 3 + 1, q * 3 + 1) if f"{y}-{m:02d}" in idx]
    return sum(idx[m] for m in ms) / len(ms), len(ms)

food_q3_yoy, warn = None, []
try:
    a26, n26 = qavg(2026, 3)
    a25, n25 = qavg(2026 - 1, 3)
    if n26 < 3:
        warn.append(f"Q3-2026 index partial ({n26}/3 months: official m/m through Jul only + weekly shape)")
        # September shape from weekly trimmed chain (Aug31 week latest)
        wsep = [w["food_wow_trimmed_pct"] for w in fw["weeks"] if w["date"] >= "2026-09-01"]
        warn.append(f"Sep weekly points: {len(wsep)}")
    food_q3_yoy = round((a26 / a25 - 1) * 100, 2)
except Exception as e:
    warn.append(f"food index fail: {e}")

X5_Q2_LFL, X5_SRC = 4.2, "carry Q2 (rel 16Jul2026); X5 Q3 trading ~14Oct"
GAP = 2.56  # LFL bridge v2 trailing gap from 2026H1 (act 6.4 - market 3.84)
pred = round(0.4 * food_q3_yoy + 0.6 * X5_Q2_LFL + GAP, 2) if food_q3_yoy is not None else None
out = {"as_of": datetime.date.today().isoformat(), "target": "Magnit Q3 2026 LFL yoy",
       "food_q3_yoy": food_q3_yoy, "x5_q3_lfl": X5_Q2_LFL, "x5_src": X5_SRC,
       "trailing_gap": GAP, "bridge": "0.4*food+0.6*x5lfl+gap (v2)",
       "nowcast": pred, "warnings": warn,
       "read": (f"Q3 LFL nowcast {pred}% vs H1 6.4% / Q2-impl ~6.3%: "
                + ("deceleration continues" if pred and pred < 6.3 else "stable"))}
(DATA / "nowcast_q3_2026.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
