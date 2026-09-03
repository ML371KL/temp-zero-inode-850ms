"""M&A add-on layer: known deals as explicit pp contributions (not buried in spread).
Deals (IFRS note 7, primary):
- Dixy: 22 Jul 2021; H2 2021 +133.9bn; pro-forma FY2021 +163.5 (H1 part); FY2022 est H1 ~150bn (+-20)
- Samberi/DV Nevada: 11 Jan 2024; 2024 +100.5bn (~25bn/q); 2023 base clean
- Azbuka: 20 May 2025; 2025 +66.0bn; H1 2025 +11.6bn; H1 2026 ~54bn EST (+-3)
Bridge v2: organic_pred = 0.4*food + 0.6*x5organic + trailing_organic_gap; reported_pred = organic_pred + ma_pp.
x5organic = X5 LFL where available (2024Q2+), else X5 total (flagged).
Saves magnit/data/ma_layer.json + tests bridge v2 on clean points.
"""
import json, pathlib

DATA = pathlib.Path(__file__).parent / "data"
food_q = json.loads((DATA / "macro" / "food_monthly.json").read_text(encoding="utf-8"))["quarterly_food_cumul_pct"]
x5 = json.loads((DATA / "peers" / "x5_quarterly.json").read_text(encoding="utf-8"))["quarters"]

DEALS = [
    {"deal": "Dixy", "close": "2021-07-22", "contrib": {"2022H1": 150.0, "2022FY": 300.0},
     "band": 20.0, "note": "H2 2021 +133.9bn (IFRS); FY2022 ~300 est (band +-20); H1 ~150"},
    {"deal": "Samberi", "close": "2024-01-11", "contrib": {"2024FY": 100.5, "2024H1": 50.0},
     "band": 5.0, "note": "2024 +100.5bn IFRS note 7; H1 ~50 (even split)"},
    {"deal": "Azbuka", "close": "2025-05-20", "contrib": {"2025FY": 66.0, "2025H1": 11.6, "2026H1": 54.0},
     "band": 3.0, "note": "IFRS note 7 exact (2025, H1-2025); H1-2026 EST ~54 (band +-3)"},
]
# bases for pp conversion (reported base revenue, bn)
BASES = {"2022H1": 822.0, "2022FY": 1856.0, "2024H1": 1229.5, "2024FY": 2544.7,
         "2025H1": 1460.1, "2025FY": 3043.4, "2026H1": 1661.6}

def chain(ql):
    p = 1.0
    for q in ql: p *= (1 + food_q[q] / 100)
    return round((p - 1) * 100, 2)

def x5org(ql):
    """X5 organic proxy: LFL mean where available else total yoy (flagged)."""
    if all(q.replace("-", "") in x5 and "x5_lfl" in x5[q.replace("-", "")] for q in ql):
        return round(sum(x5[q.replace("-", "")]["x5_lfl"] for q in ql) / len(ql), 2), "lfl"
    # fallback total yoy via levels
    tot, base = 0, 0
    for q in ql:
        qk = q.replace("-", "")
        tot += x5[qk]["revenue_mln"]
        y = int(q[:4])
        b = x5.get(f"{y-1}{qk[4:]}", {}).get("revenue_mln")
        base += b if b else 0
    return round((tot / base - 1) * 100, 1), "total-flagged"

TESTS = [  # (period, quarters, organic_act, deals_in_period {deal: contrib})
    ("2024H1", ["2024-Q1", "2024-Q2"], 15.6 - 3.2, {"Samberi": 50.0}),  # organic H1 ~12.4? recompute below
    ("2024FY", ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"], 15.6, {"Samberi": 100.5}),
    ("2025FY", ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"], 13.1, {"Azbuka": 66.0}),
    ("2026H1", ["2026-Q1", "2026-Q2"], 10.3, {"Azbuka": 54.0}),
]
# organic H1 2024: (1460.1-50)/(1229.5-0)= +14.7%? base H1 2023 has no Samberi -> organic = (1460.1-50)/1229.5-1 = 14.7
TESTS[0] = ("2024H1", ["2024-Q1", "2024-Q2"], round((1460.1 - 50.0) / 1229.5 * 100 - 100, 1), {"Samberi": 50.0})
print("period     org_act food    x5org(kind)      market  ma_pp  rep_pred rep_act  err")
gap = None
for period, ql, org_act, deals in TESTS:
    food = chain(ql)
    xo, kind = x5org(ql)
    market = 0.4 * food + 0.6 * xo
    s = 0.0 if gap is None else gap
    org_pred = market + s
    ma_pp = round(sum(deals.values()) / BASES[period] * 100, 2)
    # reported actual implied:
    rep_act = {"2024H1": 18.8, "2024FY": 19.6, "2025FY": 15.3, "2026H1": 12.8}[period]
    rep_pred = org_pred + ma_pp
    print(f"{period:<10} {org_act:>6}% {food:>6}% {xo:>6}%({kind[0]}) {market:>7.2f}% {ma_pp:>5.2f}pp {rep_pred:>7.2f}% {rep_act:>5}% {rep_pred-rep_act:>+5.2f}pp")
    gap = org_act - market

json.dump({"deals": DEALS, "method_v1": "organic bridge + ma_pp add-on (TESTED WORSE: 3.2 vs 1.9)",
           "method_v2": "LFL bridge (Magnit LFL vs X5 LFL, expansion-free) + expansion add-on + M&A add-on",
           "v2_test": {"2024FY": +1.82, "2025FY": -1.46, "2026H1": -2.56},
           "expansion_space_growth": {"2024": 5.3, "2025": 5.6, "H1_2026": 0.4},
           "note": "trailing gap per bridge; M&A no longer in spread"},
          open(DATA / "ma_layer.json", "w"), ensure_ascii=False, indent=1)
print("saved ma_layer.json")
print()
print("--- v2: LFL bridge (Magnit LFL vs X5 LFL, expansion-free both sides) ---")
LFL = {  # (magnit lfl, x5 lfl quarters mean)
    "2024FY": (11.2, (14.9 + 13.8 + 14.0 + 14.6) / 4, 11.06),
    "2025FY": (8.7, None, 5.25),  # x5 2025 LFL mean computed below
    "2026H1": (6.4, (6.1 + 4.2) / 2, 2.78),
}
import statistics as _st
_x5 = json.loads((DATA / "peers" / "x5_quarterly.json").read_text(encoding="utf-8"))["quarters"]
l25 = [_x5[q]["x5_lfl"] for q in ("2025Q1", "2025Q2", "2025Q3", "2025Q4")]
LFL["2025FY"] = (8.7, sum(l25) / 4, 5.25)
gap = None
for p, (act, xo, food) in LFL.items():
    m = 0.4 * food + 0.6 * xo
    s = 0.0 if gap is None else gap
    print(f"{p}: magnit LFL {act}% vs x5 LFL {xo:.2f}% food {food}% -> pred {m+s:.2f}% err {m+s-act:+.2f}pp")
    gap = act - m
print("v2 verdict: LFL<->LFL structural match; expansion+M&A as separate add-ons (space growth 5.3/5.6/0.4%)")
