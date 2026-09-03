"""FV distribution (magnit-v2): Monte Carlo over margin regime x WACC path x multiple x deleveraging.
Regime priors = FY margin base-rate 2019-2025 (n=6: stress 1, mid 2, healthy 3).
Posterior = prior tilted by H1-2026 evidence (trough + falling cod + capex end + organic convergence).
Method v1.1 (distress mult-only, EV floors). Seed fixed. Saves magnit/data/fv_dist.json
"""
import json, pathlib, datetime
import numpy as np

DATA = pathlib.Path(__file__).parent / "data"
wacc = json.loads((DATA / "macro" / "wacc.json").read_text(encoding="utf-8"))["scenarios"]
N = 50000
SH = 101.911355  # storage basis = issued; canonical outstanding applied at consumption (*1.5021)
CANONICAL_FACTOR = 101.911355 / 67.847
try:
    P = float(json.loads((DATA / "market" / "latest.json").read_text(encoding="utf-8"))["cap_dual"]["price"])
    P_SRC = "market/latest.json"
except Exception:
    P, P_SRC = 1580.0, "fallback (market snapshot missing)"

PRIOR = {"stress": 1 / 6, "mid": 2 / 6, "healthy": 3 / 6}
POST = {"stress": 0.20, "mid": 0.42, "healthy": 0.38}  # tilt: trough passed, cod 17.1->16.0, capex -46%, organic gap closed
BANDS = {"stress": (4.5, 5.2), "mid": (5.2, 6.2), "healthy": (6.2, 7.0)}
# regime-conditional joint parameters (stress co-moves: low margin + low mult + high WACC + high debt)
# modes anchored at scenario-table central cases: mid margin 5.4 (H1 ann.), WACC hold = current 14.11, ND mid 500
REG = {
    "stress": {"rev": 3600.0, "margin": (4.0, 4.8, 5.2), "mult": (3.0, 3.8),
               "wacc": [(15.30, 0.55), (14.11, 0.35), (11.15, 0.10)], "nd": (500.0, 530.0, 560.0),
               "interest": 85.0, "capex": 150.0},
    "mid": {"rev": 3800.0, "margin": (5.2, 5.4, 6.2), "mult": (3.5, 4.5),
            "wacc": [(15.30, 0.15), (14.11, 0.40), (11.15, 0.45)], "nd": (440.0, 500.0, 510.0),
            "interest": 62.0, "capex": 100.0},
    "healthy": {"rev": 3950.0, "margin": (6.2, 6.5, 7.0), "mult": (4.0, 5.0),
                "wacc": [(15.30, 0.05), (14.11, 0.35), (11.15, 0.60)], "nd": (400.0, 440.0, 470.0),
                "interest": 50.0, "capex": 100.0},
}
WACC_PTS = [(wacc["cut_11"]["wacc"], 0.45), (wacc["hold_14"]["wacc"], 0.40), (wacc["hike_16"]["wacc"], 0.15)]
MULT = (3.5, 4.5)
W_PASS = {"stress": (0.0, 1.0), "mid": (0.35, 0.50), "healthy": (0.45, 0.60)}  # DCF weight ranges

def dcf_ev(fcf, w, g=0.03, T=5, gg=0.04):
    pv, f = 0.0, fcf
    for t in range(1, T + 1):
        f *= (1 + gg); pv += f / (1 + w) ** t
    return pv + f * (1 + g) / (w - g) / (1 + w) ** T

def run(probs, seed, shares=SH):
    rng = np.random.default_rng(seed)
    regs = rng.choice(list(probs), size=N, p=[probs[k] for k in probs])
    out = np.empty(N)
    for i, rg in enumerate(regs):
        g = REG[rg]
        margin = rng.triangular(*g["margin"])
        ebitda = g["rev"] * margin / 100
        wacc_v = rng.choice([w for w, _ in g["wacc"]], p=[p for _, p in g["wacc"]])
        mult = rng.uniform(*g["mult"])
        # explicit normalized FCF with regime-consistent interest/capex
        da = 0.04 * g["rev"]
        tax = max(0.0, ebitda - da - g["interest"]) * 0.25
        fcf = ebitda - g["interest"] - tax - g["capex"] - 10.0
        ev_dcf = max(0.0, dcf_ev(fcf, wacc_v / 100))
        ev_mult = ebitda * mult
        if rg == "stress":
            ev = ev_mult
        else:
            a, b = W_PASS[rg]
            wd = rng.uniform(a, b)
            ev = wd * ev_dcf + (1 - wd) * ev_mult
        nd = rng.triangular(*g["nd"])
        out[i] = max(0.0, ev - nd) * 1000 / shares
    return out

def main():
    res = {}
    for name, probs in (("prior", PRIOR), ("posterior", POST)):
        for basis, shares in (("issued", SH), ("outstanding", 67.847)):
            v = run(probs, 20260904 if name == "prior" else 77, shares)
            q = np.quantile(v, [0.05, 0.25, 0.5, 0.75, 0.95])
            res[f"{name}_{basis}"] = {"probs": probs, "mean": round(float(v.mean()), 0),
                     "p05": round(float(q[0]), 0), "p25": round(float(q[1]), 0),
                     "p50": round(float(q[2]), 0), "p75": round(float(q[3]), 0),
                     "p95": round(float(q[4]), 0),
                     "p_fv_gt_p": round(float((v > P).mean()), 3)}
    post = res["posterior_outstanding"]
    print(f"posterior outstanding: mean {post['mean']:.0f} p50 {post['p50']:.0f} P(FV>{P:.0f})={post['p_fv_gt_p']:.1%}")
    json.dump({"as_of": datetime.date.today().isoformat(), "price": P, "price_src": P_SRC,
               "n_draws": N, "regimes": REG, "storage_basis": "issued 101.911355m",
               "canonical_basis": "outstanding 67.847m", "canonical_factor": CANONICAL_FACTOR,
               "results": res,
               "note": ("prior=FY margin base-rate n=6 (2020 scanned gap); posterior tilted by H1 trough/cod/capex/organic evidence (stated); "
                        "hold WACC leg 14.11 = current trailing (steady-state hold 13.64); "
                        "method v1.1: EV floors, distress mult-only")},
              open(DATA / "fv_dist.json", "w"), ensure_ascii=False, indent=1)
    print("saved fv_dist.json")

if __name__ == "__main__":
    main()
