"""Sensitivity audit on the SHARED valuation engine (imports valuation.py + REG spec).
Single weight wd with complement (1-wd) — weights always sum to 100%.
Saves magnit/data/sensitivity.json (machine-readable; report renders from it, never hardcoded).
Price from market snapshot (no hardcoded fallback: metrics vs price skipped if missing).
"""
import json, pathlib, copy
import numpy as np

DATA = pathlib.Path(__file__).parent / "data"
OUT_SHARES = 67.847  # canonical basis

import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from valuation import build_fcf, dcf_ev, blend_ev
from fv_distribution import REG

try:
    P = float(json.loads((DATA / "market" / "latest.json").read_text(encoding="utf-8"))["cap_dual"]["price"])
except Exception:
    P = None


def run_once(probs, wacc_shift=0.0, mult_shift=0.0, nd_shift=0.0, seed=7, n=20000):
    rng = np.random.default_rng(seed)
    R = copy.deepcopy(REG)
    for rg in R:
        lo, hi = R[rg]["mult"][0] + mult_shift, R[rg]["mult"][1] + mult_shift
        R[rg]["mult"] = (lo, hi)
        a, m, b = R[rg]["nd"]
        R[rg]["nd"] = (a + nd_shift, m + nd_shift, b + nd_shift)
        R[rg]["wacc"] = [(w + wacc_shift, p) for w, p in R[rg]["wacc"]]
    regs = rng.choice(list(probs), size=n, p=[probs[k] for k in probs])
    out = np.empty(n)
    for i, rg in enumerate(regs):
        g = R[rg]
        margin = rng.triangular(*g["margin"])
        ebitda = g["rev"] * margin / 100
        wv = rng.choice([w for w, _ in g["wacc"]], p=[p for _, p in g["wacc"]])
        mult = rng.uniform(*g["mult"])
        comp = build_fcf(ebitda, g["rev"])
        d = dcf_ev(comp["fcf"], wv / 100)
        ev_mult = ebitda * mult
        if rg == "stress":
            ev = ev_mult
        else:
            a, b = g["w_dcf"]
            wd = rng.uniform(a, b) if b > a else a
            ev = blend_ev(d["ev"], ev_mult, wd)
        out[i] = max(0.0, ev - rng.triangular(*g["nd"])) * 1000 / OUT_SHARES
    med = float(np.median(out))
    return {"median": round(med, 0),
            "p_fv_gt_p": round(float((out > P).mean()), 3) if P else None}


base_probs = {"stress": 0.20, "mid": 0.42, "healthy": 0.38}
cases = {
    "base": (base_probs, 0, 0, 0),
    "bear_probs": ({"stress": 0.35, "mid": 0.40, "healthy": 0.25}, 0, 0, 0),
    "bull_probs": ({"stress": 0.10, "mid": 0.40, "healthy": 0.50}, 0, 0, 0),
    "wacc_up_2pp": (base_probs, 2.0, 0, 0),
    "wacc_down_2pp": (base_probs, -2.0, 0, 0),
    "mult_down_0_5x": (base_probs, 0, -0.5, 0),
    "mult_up_0_5x": (base_probs, 0, 0.5, 0),
    "debt_up_60bn": (base_probs, 0, 0, 60),
    "debt_down_60bn": (base_probs, 0, 0, -60),
    "bear_combo": ({"stress": 0.35, "mid": 0.40, "healthy": 0.25}, 2.0, -0.5, 60),
    "bull_combo": ({"stress": 0.10, "mid": 0.40, "healthy": 0.50}, -2.0, 0.5, -60),
}
res = {"price": P, "cases": {}}
for name, (pr, ws, ms, ns) in cases.items():
    r = run_once(pr, ws, ms, ns)
    res["cases"][name] = r
    zone = "n/a" if r["p_fv_gt_p"] is None else ("above" if (r["median"] > P * 1.25 and r["p_fv_gt_p"] > 0.5)
                                                else ("overlap" if r["p_fv_gt_p"] > 0.35 else "below"))
    print(f"{name:22s} median {r['median']:>7.0f} P(FV>P)={r['p_fv_gt_p']} {zone}")
(DATA / "sensitivity.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved sensitivity.json (single-wd, shared engine)")
