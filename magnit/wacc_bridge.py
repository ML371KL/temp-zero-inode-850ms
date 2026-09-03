"""WACC bridge: CBR key rate -> Magnit cost of debt -> WACC.
cod_rule (provisional, 2 calibration points): cod = 0.92 * key_avg_trailing12m.
  FY2025: key12m=18.35 -> 16.9 vs reported 17.1 (err -0.2pp)
  H1 2026: key12m=17.30 -> 15.9 vs reported 16.0 (err -0.1pp)
WACC = cod*(1-tax)*wD + (key+ERP)*(1-wD); wD_target=0.55, tax=25%, ERP=4.5pp (stated priors).
Scenario key paths (12m fwd avg): hold 14.0 / cut to 11.0 / hike to 16.0.
Saves magnit/data/macro/wacc.json
"""
import json, pathlib, datetime

DATA = pathlib.Path(__file__).parent / "data" / "macro"
kr = json.loads((DATA / "key_rate.json").read_text(encoding="utf-8"))
QA = kr["quarterly_avg"]

def avg12m_ending(year, q):
    # quarters: current + previous 3
    qs = []
    y, qq = year, q
    for _ in range(4):
        qs.append(f"{y}-Q{qq}")
        qq -= 1
        if qq == 0: qq, y = 4, y - 1
    return sum(QA[k] for k in qs) / 4

A_COD, TAX, WD, ERP = 0.92, 0.25, 0.55, 4.5
checks = []
for (y, q), rep in [((2025, 4), 17.1), ((2026, 2), 16.0)]:
    k12 = avg12m_ending(y, q)
    pred = A_COD * k12
    checks.append({"period": f"{y}Q{q}", "key12m": round(k12, 2), "pred": round(pred, 2),
                   "reported": rep, "err": round(pred - rep, 2)})
    print(f"{y}Q{q}: key12m {k12:.2f} -> cod {pred:.2f} vs reported {rep} (err {pred-rep:+.2f}pp)")

def wacc(key_fwd, cod):
    return round(cod * (1 - TAX) * WD + (key_fwd + ERP) * (1 - WD), 2)

scen = {}
for name, kfwd in (("hold_14", 14.0), ("cut_11", 11.0), ("hike_16", 16.0)):
    cod = round(A_COD * kfwd, 2)  # steady-state: trailing converges to forward
    scen[name] = {"key_fwd": kfwd, "cod": cod, "wacc": wacc(kfwd, cod)}
    print(f"{name}: key {kfwd}% cod {cod}% WACC {scen[name]['wacc']}%")
# current: trailing12m at 2026Q3partial + key now
k12_now = avg12m_ending(2026, 3)
cod_now = round(A_COD * k12_now, 2)
now = {"key_now": kr["current"]["value"], "key12m_trailing": round(k12_now, 2),
       "cod_now": cod_now, "wacc_now": wacc(kr["current"]["value"], cod_now)}
print("now:", now)
(DATA / "wacc.json").write_text(json.dumps(
    {"rule": "cod = 0.92*key_avg12m; WACC = cod*0.75*0.55 + (key+4.5)*0.45",
     "calibration": checks, "band_pp": 1.5, "status": "provisional (2 points)",
     "scenarios": scen, "now": now,
     "source_key": "cbr.ru KeyRate", "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()},
    ensure_ascii=False, indent=1), encoding="utf-8")
print("saved wacc.json")
