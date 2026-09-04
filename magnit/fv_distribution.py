"""FV distribution (magnit-v3 engine): Monte Carlo over margin regime x WACC path x multiple x debt.
Method: JUDGMENT-WEIGHTED scenario mix (expert-set regime weights, NOT a Bayesian posterior).
Corrected FCFF via valuation.py (no interest in FCFF; D&A 2.8%; growth-linked capex/WC).
Stores decimated draws + per-regime contributions for TSR/hurdle/CVaR metrics downstream.
"""
import json, pathlib, datetime
import numpy as np

from valuation import build_fcf, dcf_ev, blend_ev

DATA = pathlib.Path(__file__).parent / "data"
wacc = json.loads((DATA / "macro" / "wacc.json").read_text(encoding="utf-8"))["scenarios"]
N = 50000
SH = 101.911355  # storage basis = issued; canonical outstanding applied via shares param
OUT_SH = 67.847
CANONICAL_FACTOR = SH / OUT_SH

try:
    _mkt = json.loads((DATA / "market" / "latest.json").read_text(encoding="utf-8"))
    P, P_SRC = float(_mkt["cap_dual"]["price"]), "market/latest.json"
except Exception:
    _old = json.loads((DATA / "fv_dist.json").read_text(encoding="utf-8")) if (DATA / "fv_dist.json").exists() else {}
    if _old.get("price"):
        P, P_SRC = float(_old["price"]), "last-good fv_dist.json (market snapshot missing; STALE)"
    else:
        raise SystemExit("no market price and no prior run: refusing hardcoded fallback")

PRIOR = {"stress": 1 / 6, "mid": 2 / 6, "healthy": 3 / 6}  # FY margin base-rate 2019-2025 (n=6; 2020 scanned gap)
POST = {"stress": 0.20, "mid": 0.42, "healthy": 0.38}  # judgment tilt: trough/cod/capex/organic (stated, not Bayes)
REG = {
    "stress": {"rev": 3600.0, "margin": (4.0, 4.8, 5.2), "mult": (3.0, 3.8),
               "wacc": [(15.30, 0.55), (14.11, 0.35), (11.15, 0.10)], "nd": (500.0, 530.0, 560.0),
               "w_dcf": (0.0, 0.0)},  # distress: mult-only (DCF memo)
    "mid": {"rev": 3800.0, "margin": (5.2, 5.4, 6.2), "mult": (3.5, 4.5),
            "wacc": [(15.30, 0.15), (14.11, 0.40), (11.15, 0.45)], "nd": (440.0, 500.0, 510.0),
            "w_dcf": (0.35, 0.50)},
    "healthy": {"rev": 3950.0, "margin": (6.2, 6.5, 7.0), "mult": (4.0, 5.0),
                "wacc": [(15.30, 0.05), (14.11, 0.35), (11.15, 0.60)], "nd": (400.0, 440.0, 470.0),
                "w_dcf": (0.45, 0.60)},
}


def run(probs, seed, shares=SH):
    rng = np.random.default_rng(seed)
    regs = rng.choice(list(probs), size=N, p=[probs[k] for k in probs])
    out = np.empty(N)
    evdcf_m, evm_m, tv_m = np.empty(N), np.empty(N), np.empty(N)
    for i, rg in enumerate(regs):
        g = REG[rg]
        margin = rng.triangular(*g["margin"])
        ebitda = g["rev"] * margin / 100
        wacc_v = rng.choice([w for w, _ in g["wacc"]], p=[p for _, p in g["wacc"]])
        mult = rng.uniform(*g["mult"])
        comp = build_fcf(ebitda, g["rev"])
        d = dcf_ev(comp["fcf"], wacc_v / 100)
        evdcf_m[i], evm_m[i], tv_m[i] = d["ev"], ebitda * mult, d["terminal_share"]
        lo, hi = g["w_dcf"]
        wd = rng.uniform(lo, hi) if hi > lo else lo
        ev = blend_ev(d["ev"], ebitda * mult, wd)
        nd = rng.triangular(*g["nd"])
        out[i] = max(0.0, ev - nd) * 1000 / shares
    return out, regs, evdcf_m, evm_m, tv_m


def summarize(v, regs, tv_m, probs, price, hurdle_2y=1.25 ** 2 - 1):
    q = np.quantile(v, [0.05, 0.25, 0.5, 0.75, 0.95])
    tsr = v / price - 1  # full-draw TSR distribution (dividends ~0 near-term, stated)
    by_reg = {}
    for rg in probs:
        m = regs == rg
        by_reg[rg] = {"share": round(float(m.mean()), 3),
                      "mean": round(float(v[m].mean()), 0),
                      "p_fv_gt_p": round(float((v[m] > price).mean()), 3),
                      "contrib_to_mean": round(float(v[m].sum() / v.sum()), 3)}
    return {"probs": probs, "mean": round(float(v.mean()), 0),
            "p05": round(float(q[0]), 0), "p25": round(float(q[1]), 0),
            "p50": round(float(q[2]), 0), "p75": round(float(q[3]), 0),
            "p95": round(float(q[4]), 0),
            "p_fv_gt_p": round(float((v > price).mean()), 3),
            "by_regime": by_reg,
            "terminal_share_mean": round(float(tv_m.mean()), 3),
            "tsr_2y": {"median": round(float(np.median(tsr)), 4),
                       "mean": round(float(tsr.mean()), 4),
                       "p_hurdle_25pa": round(float((tsr >= hurdle_2y).mean()), 3),
                       "p_any_gain": round(float((tsr > 0).mean()), 3),
                       "p_loss_30": round(float((tsr <= -0.30).mean()), 3),
                       "p_loss_50": round(float((tsr <= -0.50).mean()), 3),
                       "cvar_5": round(float(tsr[v <= q[0]].mean()), 4),
                       "mos_p25": round(float(q[1]) / price - 1, 4)}}


def main():
    res = {}
    draws = {}
    for name, probs in (("prior", PRIOR), ("judgment", POST)):
        for basis, shares in (("issued", SH), ("outstanding", OUT_SH)):
            v, regs, _, _, tv_m = run(probs, 20260904 if name == "prior" else 77, shares)
            res[f"{name}_{basis}"] = summarize(v, regs, tv_m, probs, P)
            draws[f"{name}_{basis}"] = [round(float(x), 1) for x in v[::10]]  # 5k sample
    post = res["judgment_outstanding"]
    print(f"mix outstanding: mean {post['mean']:.0f} p50 {post['p50']:.0f} P(FV>{P:.0f})={post['p_fv_gt_p']:.1%}")
    for rg, b in post["by_regime"].items():
        print(f"  {rg}: w={b['share']} mean={b['mean']} contrib={b['contrib_to_mean']}")
    json.dump({"as_of": datetime.date.today().isoformat(), "price": P, "price_src": P_SRC,
               "n_draws": N, "draw_decimation": 10, "regimes": REG,
               "storage_basis": "issued 101.911355m",
               "canonical_basis": "outstanding 67.847m", "canonical_factor": CANONICAL_FACTOR,
               "method": "judgment-weighted scenario mix (expert regime weights, NOT Bayesian posterior)",
               "results": res, "draws": draws,
               "note": ("FCFF excludes interest; D&A 2.8%; growth-linked capex/WC; "
                        "hold WACC leg 14.11 = current trailing; method v1.1 EV floors, distress mult-only")},
              open(DATA / "fv_dist.json", "w"), ensure_ascii=False, indent=1)
    print("saved fv_dist.json (mix_* keys; draws decimated x10)")


if __name__ == "__main__":
    # back-compat aliases for consumers migrating to mix_* keys
    main()
