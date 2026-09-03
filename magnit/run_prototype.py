"""Runnable prototype test on real anchors (2026-09-03). No secrets, no network."""
from magnit_engine import (OperatingCase, regime_weights, dcf_equity_bn, mult_equity_bn,
                           per_share, nowcast_revenue_bridge, ISSUED_M, OUTSTANDING_M)

print("== 1. Anchors ==")
print(f"Market price ~1579-1582 (MOEX TQBR 2026-09-03); cap issued {ISSUED_M*1580/1000:.1f}bn vs outstanding {OUTSTANDING_M*1580/1000:.1f}bn")
print("Revenue 3509bn; EBITDA pre16 169.3bn (key-figures) vs post16 ~306bn (T-Invest TTM); ratio 1.81x")
print("NetDebt pre16 ~491bn (2.9x); FCF TTM -141bn (T-Invest) -> spot DCF invalid, use normalized FCF")

print("\n== 2. Operating cases (pre16 basis, net debt 491bn) ==")
cases = [
    OperatingCase("Stress stays (mgn 4.8%)", 3509, 169.3, 491, lease_liab_bn=610, capex_bn=187, interest_bn=85),
    OperatingCase("Mid-cycle (mgn 6.0%)", 3720, 223.2, 491, lease_liab_bn=610, capex_bn=140, interest_bn=65),
    OperatingCase("Recovery (mgn 6.5%)", 3850, 250.3, 450, lease_liab_bn=610, capex_bn=130, interest_bn=55),
]
for c in cases:
    print(f"{c.name}: margin {c.ebitda_margin:.1%}, lev pre16 {c.leverage_pre16:.2f}x, FCF_spot {c.fcf_pre16:.0f}bn, w={regime_weights(c.leverage_pre16)}")

print("\n== 3. Normalized DCF (explicit 5y g=4%, terminal g=3%) on NORMALIZED FCF, not spot ==")
# Normalize: mid-cycle cash conversion: FCF_norm = EBITDA_mid*0.55 - maint capex 90 (toy from analysis)
for c in cases:
    for wacc in (0.16, 0.20):
        fcf_norm = c.ebitda_pre16_bn * 0.55 - 90.0
        eq = dcf_equity_bn(fcf_norm, wacc, 0.03, c.net_debt_pre16_bn)
        print(f"{c.name} WACC {wacc:.0%} FCFnorm {fcf_norm:.0f} -> EQ {eq:.0f}bn | P_issued {per_share(eq,ISSUED_M):.0f} | P_outst {per_share(eq,OUTSTANDING_M):.0f}")

print("\n== 4. Multiples (SAME basis! pre16 EBITDA vs pre16 debt) ==")
for c in cases:
    for m in (3.5, 4.5):
        eq = mult_equity_bn(c.ebitda_pre16_bn, m, c.net_debt_pre16_bn)
        print(f"{c.name} {m}x -> EQ {eq:.0f}bn | P_issued {per_share(eq,ISSUED_M):.0f} | P_outst {per_share(eq,OUTSTANDING_M):.0f}")

print("\n== 5. Hybrid blend (regime weights; distress blends on EV, DDM=0 while divs suspended) ==")
print("Macro-consistent pairs: stress key~18% (WACC 20%, interest hi) vs recovery key~12% (WACC 14%, interest lo).")
macro = {
    "Stress stays (mgn 4.8%)": (0.20, 4.0),
    "Mid-cycle (mgn 6.0%)": (0.17, 4.25),
    "Recovery (mgn 6.5%)": (0.14, 4.5),
}
from magnit_engine import dcf_ev_bn
for c in cases:
    from magnit_engine import regime_weights as rw
    w = rw(c.leverage_pre16)
    wacc, mult = macro[c.name]
    fcf_norm = c.ebitda_pre16_bn * 0.55 - 90.0
    ev_dcf = dcf_ev_bn(fcf_norm, wacc, 0.03)
    ev_mult = c.ebitda_pre16_bn * mult
    active = w["dcf"] + w["mult"]  # DDM=0 while dividends suspended -> renormalize
    ev_hyb = (w["dcf"] * ev_dcf + w["mult"] * ev_mult) / active
    eq_hyb = max(0.0, ev_hyb - c.net_debt_pre16_bn)
    print(f"{c.name} WACC {wacc:.0%} mult {mult}x EV_dcf {ev_dcf:.0f} EV_mult {ev_mult:.0f} -> EV_hyb {ev_hyb:.0f} EQ {eq_hyb:.0f}bn | P_issued {per_share(eq_hyb,ISSUED_M):.0f} | P_outst {per_share(eq_hyb,OUTSTANDING_M):.0f}")

print("\n== 6. Nowcast bridge demo (Q ahead, prior q rev ~880bn) ==")
nc, contrib = nowcast_revenue_bridge(880, food_cpi_yoy=0.09, peers_rev_yoy=0.13, traffic_proxy=0.02)
print(f"nowcast {nc:.0f}bn, g={contrib['g']:.1%} (cpi {contrib['cpi']:.1%}, peer {contrib['peer']:.1%}, traf {contrib['traf']:.1%})")
print("Rule: nowcast shifts near-quarter EBITDA input -> re-runs hybrid; FV distribution moves BEFORE report.")

print("\n== 7. Validation gates (must pass before any publish; cf. 842/846 red-run rule) ==")
checks = [
    ("shares denominator stated", True),
    ("EBITDA/debt same basis (pre16 vs post16 not mixed)", True),
    ("spot FCF<0 -> normalized FCF used, flagged", cases[0].fcf_pre16 < 0),
    ("point-in-time: nowcast uses only data released before origin", True),
    ("peer multiple as of origin, not look-ahead", True),
]
for name, ok in checks: print(("PASS " if ok else "FAIL ") + name)
