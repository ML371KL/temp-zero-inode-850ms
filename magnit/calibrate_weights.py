"""Step 3: nowcast-weight backtest harness + frozen constants (cf. 842 constants.py rule).

Honest status: n=3 annual LFL points (11.2 -> 8.7 -> 6.4*annualized) is NOT enough
to estimate (w_cpi, w_peer, w_traf). This script:
  1) runs a directional leave-one-out check with documented proxy stubs,
  2) grid-searches weights to SHOW overfit risk (many weights fit 3 points),
  3) FREEZES priors unchanged + wide uncertainty, with recalibration trigger.
Saves magnit/data/calibration_report.json + writes magnit/constants.py (versioned).
"""
import json, itertools, pathlib
import numpy as np

DATA = pathlib.Path(__file__).parent / "data"

# Real LFL anchors from registry (primary source), pct_yoy
ACTUAL = {"FY2024": 11.2, "FY2025": 8.7, "1H2026": 6.4}
# Proxy stubs (CLEARLY marked; vintages not yet collected point-in-time):
# food CPI yoy, peer (X5) revenue yoy, traffic proxy. Values are illustrative placeholders
# to test mechanics, NOT for production. Full backtest needs Rosstat weekly + X5 archive.
PROXY = {"FY2024": (9.5, 13.0, 1.0), "FY2025": (10.5, 14.0, 0.5), "1H2026": (9.0, 13.0, 0.3)}
PRIORS = (0.35, 0.45, 0.20)

def bridge(proxies, w):
    cpi, peer, tr = proxies
    return w[0]*cpi + w[1]*peer + w[2]*tr

def main():
    keys = list(ACTUAL.keys())
    # 1) priors: directional check (deceleration predicted?)
    preds = {k: bridge(PROXY[k], PRIORS) for k in keys}
    print("priors preds vs actual:")
    for k in keys:
        print(f"  {k}: pred {preds[k]:.2f}% vs actual {ACTUAL[k]:.2f}%")
    # direction: FY24->FY25 actual down; pred down?
    dir_ok = (preds["FY2025"] - preds["FY2024"]) < 0 and (ACTUAL["FY2025"] - ACTUAL["FY2024"]) < 0
    print("direction FY24->FY25:", "OK" if dir_ok else "FAIL")
    # 2) grid search to demonstrate overfit: many weights get MAE < 1pp on n=3
    best, n_good = None, 0
    for w in itertools.product([0.2, 0.35, 0.5], [0.3, 0.45, 0.6], [0.05, 0.2, 0.35]):
        if abs(sum(w) - 1.0) > 1e-9: continue
        mae = float(np.mean([abs(bridge(PROXY[k], w) - ACTUAL[k]) for k in keys]))
        if mae < 1.0: n_good += 1
        if best is None or mae < best[0]: best = (mae, w)
    print(f"grid: {n_good} weight vectors achieve MAE<1pp on n=3 -> OVERFIT RISK, priors frozen")
    print(f"best in grid: MAE {best[0]:.2f} w={best[1]} (NOT adopted)")
    report = {
        "engine_version": "magnit-v0",
        "n_obs": len(keys),
        "priors": {"w_cpi": PRIORS[0], "w_peer": PRIORS[1], "w_traf": PRIORS[2]},
        "priors_mae_pp": float(np.mean([abs(preds[k]-ACTUAL[k]) for k in keys])),
        "direction_check": "pass" if dir_ok else "fail",
        "grid_overfit_note": f"{n_good} vectors with MAE<1pp on n=3: weights NOT re-estimated",
        "proxy_status": "STUB - Rosstat weekly food CPI + X5 archive vintages required for production",
        "recalibration_trigger": ">=12 quarterly origins with point-in-time proxies, then purged expanding-window OOS",
        "regime_weights": {"distress_lev_ge_2.5": {"dcf": 0.25, "mult": 0.75, "ddm": 0.0, "blend_on": "EV"},
                           "mid_lev_1.5_2.5": {"dcf": 0.45, "mult": 0.40, "ddm": 0.15, "blend_on": "EV-renorm"},
                           "healthy_lev_lt_1.5": {"dcf": 0.55, "mult": 0.30, "ddm": 0.15, "blend_on": "EV-renorm"}},
        "frozen": True,
    }
    (DATA / "calibration_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    const = '''"""Frozen calibration (magnit-v0). Eyeball refit forbidden; change only via recalibration trigger in calibration_report.json."""
ENGINE_VERSION = "magnit-v0"
W_CPI, W_PEER, W_TRAF = 0.35, 0.45, 0.20
W_PRIORS_MAE_PP = %(mae).2f  # on n=3 stub proxies; wide uncertainty
REGIME_WEIGHTS = {
    "distress": {"dcf": 0.25, "mult": 0.75, "ddm": 0.0, "blend_on": "EV"},
    "mid": {"dcf": 0.45, "mult": 0.40, "ddm": 0.15, "blend_on": "EV-renorm"},
    "healthy": {"dcf": 0.55, "mult": 0.30, "ddm": 0.15, "blend_on": "EV-renorm"},
}
SHARES_ISSUED_M = 101.911355
SHARES_OUTSTANDING_M = 67.871  # verify vs FY2025 annual report treasury note
RECALIBRATION_TRIGGER = ">=12 quarterly origins point-in-time"
''' % {"mae": report["priors_mae_pp"]}
    (pathlib.Path(__file__).parent / "constants.py").write_text(const, encoding="utf-8")
    print("frozen constants.py written; calibration_report.json saved")

if __name__ == "__main__":
    main()
