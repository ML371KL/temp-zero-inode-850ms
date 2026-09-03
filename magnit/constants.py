"""Frozen calibration (magnit-v1). Eyeball refit forbidden; change only via recalibration trigger.
v0 (2026-09-03): stub proxies, direction FAIL -> priors frozen, spread term required.
v1 (2026-09-04): REAL proxies (Rosstat official food CPI + X5 revenue), bridge
  rev_yoy = 0.4*food_q + 0.6*x5 + trailing_gap; direction PASS (2/2), MAE 1.78pp on n=3.
  Weekly trimmed-mean food wow validated vs official within ~0.5pp (except summer veg season).
"""
ENGINE_VERSION = "magnit-v1"
# nowcast bridge v1 (revenue yoy, quarterly)
A_FOOD, B_PEER = 0.4, 0.6
SPREAD_RULE = "trailing Magnit-minus-market gap (point-in-time, 1-period lag)"
V1_MAE_PP = 1.78
V1_DIRECTION = "pass"
W_CPI, W_PEER, W_TRAF = 0.35, 0.45, 0.20  # v0 LFL-bridge priors, superseded by v1 revenue bridge
REGIME_WEIGHTS = {
    "distress": {"dcf": 0.25, "mult": 0.75, "ddm": 0.0, "blend_on": "EV"},
    "mid": {"dcf": 0.45, "mult": 0.40, "ddm": 0.15, "blend_on": "EV-renorm"},
    "healthy": {"dcf": 0.55, "mult": 0.30, "ddm": 0.15, "blend_on": "EV-renorm"},
}
SHARES_ISSUED_M = 101.911355
SHARES_TREASURY_M = 34.064  # IFRS FY2025 note: own shares bought back
SHARES_OUTSTANDING_M = 67.847  # IFRS FY2025 circulation; T-Invest 67.871 stale -> use 67.847
# Canonical per-share basis = OUTSTANDING (ex-treasury): price discovery happens on tradeable
# shares; treasury economics accrue to remaining holders (cancel/sell/M&A/REPO optionality).
# Issued basis is shown only to reconcile MOEX-published cap (which overstates economic cap).
SHARES_CANONICAL_M = SHARES_OUTSTANDING_M
OUTSTANDING_FACTOR = SHARES_ISSUED_M / SHARES_OUTSTANDING_M  # 1.5021: issued-basis FV -> canonical
# verified FY2025 anchors (bn rub unless noted)
FY2025 = {"revenue": 3509.2, "ebitda_pre16": 169.3, "ebitda_post16": 306.2,
          "net_debt_pre16": 496.3, "net_debt_post16": 1096.3, "leases": 600.1,
          "loans": 745.7, "capex_exMA": 187.1, "cost_of_debt_pct": 17.1,
          "da_rou": 159.4, "lease_cash_out": 57.0}
H1_2026 = {"revenue": 1887.2, "ebitda_pre16": 96.0, "ebitda_post16": 171.8,
           "ebitda_margin_pre16": 0.051, "net_debt_pre16": 518.1, "net_debt_post16": 1138.6,
           "capex_exMA": 36.8, "cost_of_debt_pct": 16.0, "net_loss": -1.9}
RECALIBRATION_TRIGGER = ">=12 quarterly origins, traffic split, M&A-adjusted LFL base"
