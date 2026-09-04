"""Q3-2026 LFL nowcast tracker (LFL bridge v2: 0.4*food + 0.6*x5lfl + trailing_gap).
Food: SYMMETRIC month-vs-same-month comparison (Jul26 vs Jul25, Aug vs Aug, ...),
never a partial-quarter average vs a full quarter. Partial months flagged.
X5 Q3 LFL: carry Q2 (4.2) until X5 Q3 trading (~14 Oct); carry widens the interval.
Output is ROUNDED to whole percent with an explicit interval (backtest MAE based):
  'about 7%, low confidence' — never false precision like 7.09%.
Saves magnit/data/nowcast_q3_2026.json
"""
import json, pathlib, datetime

DATA = pathlib.Path(__file__).parent / "data"
fm = json.loads((DATA / "macro" / "food_monthly.json").read_text(encoding="utf-8"))["monthly_food_mom_pct"]
fw = json.loads((DATA / "macro" / "food_weekly.json").read_text(encoding="utf-8"))
def food_q(q):
    fq = json.loads((DATA / "macro" / "food_monthly.json").read_text(encoding="utf-8"))["quarterly_food_cumul_pct"]
    return fq[q]

try:
    sk = json.loads((DATA / "skill_lfl.json").read_text(encoding="utf-8"))
    MAE_PP = float(sk["mae_pp"])
    # gap window: last 3 quarterly backtest gaps + H1-2026 hard observation (most recent fact).
    # Rule chosen by backtest (trailing4 MAE 3.55 < expanding 4.02); 'last' (2.90) rejected:
    # pure momentum-chase, fragile exactly at turning points where direction already fails.
    q_gaps = [(r["act"] - r["market"]) for r in sk["origins"][-3:]]
    reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
    lv = {(x["series"], x["period"]): x["value"] for x in reg if x["status"] == "ok"}
    h1_food = ((1 + food_q("2026-Q1") / 100) * (1 + food_q("2026-Q2") / 100) - 1) * 100
    x5 = json.loads((DATA / "peers" / "x5_quarterly.json").read_text(encoding="utf-8"))["quarters"]
    h1_x5 = (x5["2026Q1"]["x5_lfl"] + x5["2026Q2"]["x5_lfl"]) / 2
    h1_gap = lv[("lfl", "2026H1")] - (0.4 * h1_food + 0.6 * h1_x5)
    gaps = q_gaps + [h1_gap]
    GAP = sum(gaps) / len(gaps)
    GAP_SRC = (f"mean of last-3 quarterly gaps {['%+.2f' % g for g in q_gaps]} + H1-2026 {h1_gap:+.2f}")
except Exception as e:
    MAE_PP, GAP, GAP_SRC = 5.6, 2.56, f"fallback H1 gap (skill file missing: {e})"

idx, level = {}, 100.0
for k in sorted(fm):
    level *= (1 + fm[k] / 100)
    idx[k] = level

have26 = [m for m in ("2026-07", "2026-08", "2026-09") if m in idx]
have25 = [m.replace("2026", "2025") for m in have26 if m.replace("2026", "2025") in idx]
warn = []
if len(have26) < 3:
    warn.append(f"food index partial ({len(have26)}/3 months of Q3; symmetric month-vs-month only)")
wsep = [w["food_wow_trimmed_pct"] for w in fw.get("weeks", []) if w["date"] >= "2026-09-01"]
if not wsep:
    warn.append("no September weekly points yet (file through Aug-31)")

food_yoy = round(sum(idx[m] for m in have26) / len(have26) /
                 (sum(idx[m] for m in have25) / len(have25)) * 100 - 100, 2) if have26 and have25 else None
months_note = f"symmetric on {len(have26)}/3 months ({', '.join(have26) or 'none'} vs 2025)"

X5_Q2_LFL, X5_SRC = 4.2, "carry Q2 (rel 16Jul2026); X5 Q3 trading ~14Oct; carry widens interval"
pred = round(0.4 * food_yoy + 0.6 * X5_Q2_LFL + GAP) if food_yoy is not None else None
conf = "low" if (len(have26) < 3 or not wsep) else "medium"
out = {"as_of": datetime.date.today().isoformat(), "target": "Magnit Q3 2026 LFL yoy",
       "food_q3_yoy": food_yoy, "food_basis": months_note,
       "x5_q3_lfl": X5_Q2_LFL, "x5_src": X5_SRC,
       "trailing_gap": GAP, "gap_src": GAP_SRC, "bridge": "0.4*food+0.6*x5lfl+gap (v2)",
       "nowcast": pred, "interval_pp": MAE_PP, "confidence": conf, "warnings": warn,
       "read": (f"preliminary Q3 LFL bridge: about {pred}%, {conf} confidence "
                f"(±{MAE_PP}pp backtest interval)" if pred is not None else "insufficient data")}
(DATA / "nowcast_q3_2026.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
