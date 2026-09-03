"""Recalibration v1 with REAL proxies (replaces stub-based v0 verdict).
Bridge (revenue yoy): pred = A*food_q + B*x5 + spread, (A,B)=(0.4,0.6) renormalized priors.
spread_origin = trailing Magnit-X5 gap (point-in-time: only prior periods).
Origins: FY2024, FY2025, 1H2026. Verdict: direction + MAE. Freeze v1 only on full pass.
"""
import json, pathlib

DATA = pathlib.Path(__file__).parent / "data"
food_q = json.loads((DATA / "macro" / "food_monthly.json").read_text(encoding="utf-8"))["quarterly_food_cumul_pct"]

def chain(qs):
    p = 1.0
    for q in qs: p *= (1 + food_q[q] / 100)
    return round((p - 1) * 100, 2)

ACT = {  # (magnit_rev_yoy, food_cumul, x5_rev_yoy)
    "FY2024": (19.6, chain(["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"]), 24.2),
    "FY2025": (15.3, chain(["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]), 18.8),
    "1H2026": (12.8, chain(["2026-Q1", "2026-Q2"]), 10.6),  # x5 H1 ~= mean(Q1,Q2), flagged approx
}
A, B = 0.4, 0.6
print(f"{'origin':<8} {'magnit':>7} {'food':>7} {'x5':>7} {'market':>7} {'spread_used':>11} {'pred':>7} {'err':>7}")
errs, dirs_pred, dirs_act = [], [], []
prev_gap = None
prev_act = None
ok_dir = True
for org, (act, food, x5) in ACT.items():
    market = A * food + B * x5
    spread = 0.0 if prev_gap is None else prev_gap  # point-in-time trailing gap
    pred = market + spread
    err = pred - act
    errs.append(abs(err))
    if prev_act is not None:
        dp = (pred - prev_pred) < 0
        da = (act - prev_act) < 0
        dirs_pred.append(dp); dirs_act.append(da)
        if dp != da: ok_dir = False
        print(f"{org:<8} {act:>6.1f}% {food:>6.2f}% {x5:>6.1f}% {market:>6.2f}% {spread:>+10.2f}% {pred:>6.2f}% {err:>+6.2f}pp  dir_pred={'down' if dp else 'up'} dir_act={'down' if da else 'up'}")
    else:
        print(f"{org:<8} {act:>6.1f}% {food:>6.2f}% {x5:>6.1f}% {market:>6.2f}% {'(seed)':>11} {pred:>6.2f}% {err:>+6.2f}pp")
    prev_gap = act - market  # trailing gap for next origin (uses actual incl. M&A/Samberi effects)
    prev_act, prev_pred = act, pred

mae = sum(errs) / len(errs)
print(f"\nMAE {mae:.2f}pp | direction: {'PASS' if ok_dir else 'FAIL'} | gaps (magnit-x5 market): FY24 {ACT['FY2024'][0]-(A*ACT['FY2024'][1]+B*ACT['FY2024'][2]):+.2f}pp ...")
print("NOTE: gaps embed M&A (Samberi Jan24, Azbuka May25) + promo drag/recovery -> spread is idiosyncratic alpha, not noise.")
report = {"engine_version": "magnit-v1", "bridge": "rev = 0.4*food_q + 0.6*x5 + trailing_gap",
          "origins": {k: {"act": v[0], "food": v[1], "x5": v[2]} for k, v in ACT.items()},
          "mae_pp": round(mae, 2), "direction": "pass" if ok_dir else "fail",
          "x5_H1_approx": "mean(Q1,Q2); refine with X5 H1 press weights",
          "food_Q": "official monthly chain-linked; weekly trimmed-mean for intra-quarter shape only",
          "recalibration_trigger": ">=12 quarterly origins, traffic split, M&A-adjusted like-for-like base"}
(DATA / "calibration_report_v1.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved calibration_report_v1.json")
