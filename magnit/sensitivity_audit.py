"""Sensitivity audit: how P(FV>P) and median move under prior perturbations.
Varies regime probs, WACC cut-prob, mult band, ND level. Verdict is ROBUST only if
WAIT/HOLD conclusion survives plausible perturbations.
"""
import json, pathlib, itertools
import numpy as np

DATA = pathlib.Path("magnit/data/fv_dist.json")
spec = json.loads(pathlib.Path("magnit/data/fv_dist.json").read_text(encoding="utf-8"))
P = 1580.0

import sys
sys.path.insert(0, "magnit")
from fv_distribution import dcf_ev, REG, SH
OUT_SHARES = 67.847  # canonical basis
import copy

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
        da = 0.04 * g["rev"]
        tax = max(0.0, ebitda - da - g["interest"]) * 0.25
        fcf = ebitda - g["interest"] - tax - g["capex"] - 10.0
        ev_dcf = max(0.0, dcf_ev(fcf, wv / 100))
        ev_mult = ebitda * mult
        if rg == "stress":
            ev = ev_mult
        else:
            a, b = (0.35, 0.50) if rg == "mid" else (0.45, 0.60)
            ev = rng.uniform(a, b) * ev_dcf + (1 - rng.uniform(a, b)) * ev_mult
        out[i] = max(0.0, ev - rng.triangular(*g["nd"])) * 1000 / OUT_SHARES
    return float(np.median(out)), float((out > P).mean())

base_probs = {"stress": 0.20, "mid": 0.42, "healthy": 0.38}
cases = {
    "base": (base_probs, 0, 0, 0),
    "bear probs (s.35/m.40/h.25)": ({"stress": 0.35, "mid": 0.40, "healthy": 0.25}, 0, 0, 0),
    "bull probs (s.10/m.40/h.50)": ({"stress": 0.10, "mid": 0.40, "healthy": 0.50}, 0, 0, 0),
    "wacc +2pp": (base_probs, 2.0, 0, 0),
    "wacc -2pp": (base_probs, -2.0, 0, 0),
    "mult -0.5x": (base_probs, 0, -0.5, 0),
    "mult +0.5x": (base_probs, 0, 0.5, 0),
    "debt +60bn": (base_probs, 0, 0, 60),
    "debt -60bn": (base_probs, 0, 0, -60),
    "bear combo (s35, w+2, m-0.5, d+60)": ({"stress": 0.35, "mid": 0.40, "healthy": 0.25}, 2.0, -0.5, 60),
    "bull combo (s10, w-2, m+0.5, d-60)": ({"stress": 0.10, "mid": 0.40, "healthy": 0.50}, -2.0, 0.5, -60),
}
print(f"{'case':38s} {'median':>7} {'P(FV>P)':>8}  price-vs-dist")
for name, (pr, ws, ms, ns) in cases.items():
    med, prob = run_once(pr, ws, ms, ns)
    zone = "above" if (med > P * 1.25 and prob > 0.5) else ("overlap" if prob > 0.35 else "below")
    print(f"{name:38s} {med:>7.0f} {prob:>7.1%}  {zone}")
