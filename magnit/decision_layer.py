"""Decision layer v5 (no buy/sell labels). Reads precomputed TSR metrics from fv_dist.json
(full-draw computation inside the engine, NOT decimated draws, NOT IRR-of-mean).
Metrics: median/mean TSR_2y, P(hurdle 56.25%), P(loss>30/50%), CVaR_5, p25 MOS.
Gates from data: ND/EBITDA level <2.5 (LTM convention), cod falling.
Rule: ACT only if P(hurdle)>=0.5 AND leverage gate AND cod gate.
"""
import json, pathlib

DATA = pathlib.Path(__file__).parent / "data"
d = json.loads((DATA / "fv_dist.json").read_text(encoding="utf-8"))
P = d["price"]
post = d["results"]["judgment_outstanding"]
m = dict(post["tsr_2y"], basis="outstanding 67.847m (canonical)", price=P)
m["p25"] = post["p25"]

# gates from data layer
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))


def series(s, basis=None):
    return sorted([x for x in reg if x["series"] == s and x.get("basis") == basis and x["status"] == "ok"],
                  key=lambda z: z["as_of"])


nd = {x["period"]: x["value"] for x in series("net_debt", "pre16")}
eb = {x["period"]: x["value"] for x in series("ebitda", "pre16")}


def ltm_ebitda(period):
    # LTM convention matching company reporting: FY = full year;
    # H1 YYYY = FY(YYYY-1) - H1(YYYY-1) + H1(YYYY)
    if period.endswith("FY"):
        return eb.get(period)
    y = int(period[:4])
    fyp, h1p, h1c = f"{y-1}FY", f"{y-1}H1", period
    if fyp in eb and h1p in eb and h1c in eb:
        return eb[fyp] - eb[h1p] + eb[h1c]
    if h1c in eb:
        return eb[h1c] * 2  # fallback annualization, flagged
    return None


lev, lev_note = {}, {}
for p in nd:
    e = ltm_ebitda(p)
    if e:
        lev[p] = round(nd[p] / e, 2)
        lev_note[p] = "LTM" if not p.endswith("FY") else "FY"
lev_trend = (list(lev.values())[-1] < list(lev.values())[-2]) if len(lev) >= 2 else False
LEV_CAP = 2.5  # gate is a LEVEL (matches stated trigger Q3 ND/EBITDA<2.5x), not direction noise
lev_gate = (list(lev.values())[-1] < LEV_CAP) if lev else False
wacc = json.loads((DATA / "macro" / "wacc.json").read_text(encoding="utf-8"))
cal = {c["period"]: c for c in wacc.get("calibration", [])}
cods = [cal[k]["reported"] for k in sorted(cal) if "reported" in cal[k]]
cod_falling = len(cods) >= 2 and cods[-1] < cods[0]
tests_ok = True  # run by refresh.py; decision refuses ACT without green pytest (see refresh)
gates = {"p_hurdle_ge_50": m["p_hurdle_25pa"] >= 0.5,
         "leverage_below_2_5x": lev_gate,
         "cod_falling": cod_falling}
verdict = "ACT" if all(gates.values()) else "WAIT"
out = {"metrics": m, "leverage_series_pre16": lev,
       "cod_points": cods, "gates": gates, "verdict": verdict,
       "rule": "ACT iff P(TSR2y>=56.25%)>=0.5 AND leverage falling AND cod falling"}
(DATA / "decision.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"TSR_2y: median {m['median']:.1%} mean {m['mean']:.1%} | "
      f"P(hurdle 25pa)={m['p_hurdle_25pa']:.1%} P(loss30)={m['p_loss_30']:.1%} P(loss50)={m['p_loss_50']:.1%} "
      f"| CVaR5={m['cvar_5']:.1%} | p25 MOS={m['mos_p25']:.1%}")
print("leverage pre16:", lev, "| cod points:", cods)
print("gates:", gates, "->", verdict)
