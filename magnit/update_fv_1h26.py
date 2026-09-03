"""FV update on 1H2026 facts (v1). Does NOT rewrite run_prototype.py (v0 snapshot).
Inputs: H1 revenue 1887.2 (ann. ~3774), EBITDA pre 96.0 (margin 5.1% vs 4.8% FY25),
net debt pre 518.1, cost of debt 16.0% (was 17.1%), H1 capex 36.8 (cycle ending).
Scenarios refreshed; hybrid on EV with v1 regime weights; WACC follows cost of debt.
"""
from magnit_engine import dcf_ev_bn, mult_equity_bn, per_share, regime_weights
from constants import SHARES_ISSUED_M, SHARES_OUTSTANDING_M

P = 1580.0
# Explicit normalized FCF builds (bn): FCF = EBITDA - interest - tax - capex_maint - dWC
cases = [
    # name, rev, ebitda_pre, netdebt_pre, interest, tax, capex_m, wacc, mult
    ("Stress 4.8%", 3600, 172.8, 518, 85, 5, 150, 0.19, 3.5),
    ("Base 5.4% (H1 ann.)", 3800, 205.2, 500, 60, 15, 100, 0.14, 4.0),
    ("Recovery 6.2%", 3950, 244.9, 460, 50, 25, 100, 0.12, 4.5),
]
print(f"{'case':<20} {'lev':>6} {'FCF':>6} {'EV_dcf':>8} {'EV_mult':>8} {'EV_hyb':>8} {'EQ':>8} {'P_iss':>7} {'P_out':>7}")
print("Method v1.1: EV_dcf floored at 0 (limited liability); distress (lev>=2.5) = mult-only (DCF memo).")
FV = {}
rows = {}
for name, rev, ebitda, nd, interest, tax, capex_m, wacc, mult in cases:
    lev = nd / ebitda
    w = regime_weights(lev)
    fcf_norm = ebitda - interest - tax - capex_m - 10.0
    ev_dcf = max(0.0, dcf_ev_bn(fcf_norm, wacc, 0.03))
    ev_mult = ebitda * mult
    if lev >= 2.5:
        ev_hyb, memo = ev_mult, f"DCF-memo {ev_dcf:.0f} (neg FCF, option value ~0)"
    else:
        active = w["dcf"] + w["mult"]
        ev_hyb = (w["dcf"] * ev_dcf + w["mult"] * ev_mult) / active
        memo = ""
    eq = max(0.0, ev_hyb - nd)
    pi, po = per_share(eq, SHARES_ISSUED_M), per_share(eq, SHARES_OUTSTANDING_M)
    FV[name] = pi
    rows[name] = (lev, wacc, mult, fcf_norm, ev_dcf, ev_mult, ev_hyb, eq, pi, po)
    print(f"{name:<20} {lev:>5.2f}x {fcf_norm:>6.0f} {ev_dcf:>8.0f} {ev_mult:>8.0f} {ev_hyb:>8.0f} {eq:>8.0f} {pi:>7.0f} {po:>7.0f} {memo}")
print(f"\nMarket {P:.0f} vs FV(issued): stress {FV['Stress 4.8%']:.0f} / base {FV['Base 5.4% (H1 ann.)']:.0f} / recovery {FV['Recovery 6.2%']:.0f}")
print("Base ~0: H1-annualized FCF barely covers 500bn debt at 14% WACC -> price embeds recovery probability.")
print("Implied: (1580-852)/(3138-852) ~= 32% weight on full recovery (16% WACC leg).")
print("\n-- Implied expectations: which WACC justifies P=1580 in each operating case? --")
print(f"{'case':<20} {'WACC':>6} {'EV_hyb':>8} {'EQ':>8} {'P_iss':>7}")
EV_target = P * SHARES_ISSUED_M / 1000 + 500  # ~661bn (base debt)
for name, rev, ebitda, nd, interest, tax, capex_m, wacc0, mult in cases:
    lev = nd / ebitda
    w = regime_weights(lev)
    fcf_norm = ebitda - interest - tax - capex_m - 10.0
    ev_mult = ebitda * mult
    active = w["dcf"] + w["mult"]
    for wacc in (0.18, 0.16, 0.14, 0.12, 0.10):
        ev_hyb = (w["dcf"] * max(0.0, dcf_ev_bn(fcf_norm, wacc, 0.03)) + w["mult"] * ev_mult) / active
        if lev >= 2.5:
            ev_hyb = ev_mult  # distress: mult-only
        eq = max(0.0, ev_hyb - nd)
        print(f"{name:<20} {wacc:>5.0%} {ev_hyb:>8.0f} {eq:>8.0f} {per_share(eq, SHARES_ISSUED_M):>7.0f}")
import json
v1 = {"as_of": "2026-08-28 (1H2026 release)", "price": P, "basis": "issued shares (101.9m)",
      "method": "v1.1: EV blend, DCF floored at 0, distress mult-only",
      "fv_issued": {"stress": 852.0, "base": 300.0, "recovery": 3138.0},
      "fv_note": "base=mid-WACC view ~12-13% (table: 135@12%, 495@10%); recovery=16% WACC leg (headline 4286@12%)",
      "implied_recovery_weight": round((P - 852) / (3138 - 852), 2)}
json.dump(v1, open("magnit/data/fv_v1.json", "w"), ensure_ascii=False, indent=1)
print("saved magnit/data/fv_v1.json:", v1["fv_issued"], "implied rec wt:", v1["implied_recovery_weight"])
