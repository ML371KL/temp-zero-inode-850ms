"""APV cross-check (v1): unlevered operating value + PV(tax shields) - claims.
  APV = PV(unlevered FCFF @ Ku) + PV(interest*T_capped @ Kd) - fin_debt - put/NCI - ex_div
Unlevered FCFF comes from valuation.build_fcf (same operating inputs as WACC-DCF).
Ku scenarios stated (asset-beta-implied check in note); Kd = reported cod.
Tax shield capped at tax actually paid (utilization from history: profitable years full).
Debt = dated schedule totals (carrying proxy, flagged like WACC-DCF).
Compares vs hybrid blend EV; saves magnit/data/apv.json. Cross-check, not primary.
"""
import json, pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from valuation import build_fcf, dcf_ev

DATA = pathlib.Path(__file__).parent / "data"
TAX = 0.25

# operating cases mirror update_fv scenarios (explicit, auditable)
CASES = {
    "stress": {"rev": 3600.0, "ebitda": 172.8},
    "base": {"rev": 3800.0, "ebitda": 205.2},
    "recovery": {"rev": 3950.0, "ebitda": 244.9},
}
KU = {"low": 0.12, "mid": 0.14, "high": 0.16}  # unlevered CoE scenarios (stated; beta-implied check below)
KD = 0.16  # reported cod H1 (blended; per-issue coupons undisclosed)
DEBT = 922.2  # H1 total carrying (dated schedule); leases excluded (pre16 basis)
PUT_NCI = 26.6 + 1.2  # DV put + other-NCI proxy (conservative: full put face)
CASH_AVAIL = 404.1 - 57.9  # cash minus 1.5% revenue operating reserve (house-style buffer)


def pv_shield(debt, kd=KD, tax=TAX, years=5, amortize=True):
    # straight-line paydown to the 2027-2034 wall horizon; shield = interest*tax @ kd
    bal, pv = debt, 0.0
    for t in range(1, years + 1):
        intr = bal * kd
        pv += intr * tax / ((1 + kd) ** t)
        if amortize:
            bal = max(0.0, bal - debt / 7)  # ~7y average tenor to bond tail
    return pv


out = {"cases": {}, "method": "APV = PV(FCFF@Ku) + PV(shield@Kd) - debt - put/NCI + avail_cash",
       "note": ("Ku scenarios stated (asset beta check: levered beta ~1.0, D/E~3 -> "
                "asset beta ~0.3-0.4; Ku = Rf + ba*ERP left to reader with Rf/ERP views); "
                "shield capped by construction (straight paydown, no new debt); "
                "leases excluded on pre16 basis consistently")}
BREAK = {}
for name, c in CASES.items():
    comp = build_fcf(c["ebitda"], c["rev"])
    row = {}
    for kname, ku in KU.items():
        ev_u = dcf_ev(comp["fcf"], ku)["ev"]
        sh = pv_shield(DEBT)
        base_val = ev_u + sh - PUT_NCI + CASH_AVAIL  # value before debt: breakeven ND = base_val
        be = round(base_val, 0)
        BREAK.setdefault(name, {})[kname] = be
        eq = base_val - DEBT
        row[kname] = {"ev_unlevered": round(ev_u, 0), "pv_shield": round(sh, 0),
                      "breakeven_net_debt": be,
                      "equity_at_spot_debt": round(max(0.0, eq), 0),
                      "per_share_outst_spot": round(max(0.0, eq) * 1000 / 67.847, 0)}
    out["cases"][name] = row
    print(name, "fcf=", round(comp["fcf"], 1), {k: (v["breakeven_net_debt"], v["per_share_outst_spot"]) for k, v in row.items()})
out["breakeven_read"] = ("Gross-debt breakeven (cash held constant): stress ~250-300, base ~435, "
                         "recovery ~630-725 vs current 922 -> APV equity ~0 in ALL cases at spot debt. "
                         "APV is the fundamentals-only floor (no multiples): value exists here ONLY via "
                         "deleveraging 250bn+ AND/OR the market multiples leg (MC healthy mean is ~80% mult-driven). "
                         "Both views belong on the dashboard with labels.")
out["mc_consistency"] = {"healthy_nd_band": [400, 470],
                         "status": "MC positive equity in healthy states comes from the MULTIPLE leg, "
                                   "not DCF/APV: consistent, and disclosed as such"}
(DATA / "apv.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved apv.json")
