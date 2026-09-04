"""Frozen calibration (magnit-v2). Eyeball refit forbidden; change only via recalibration trigger.
v2 (2026-09-04): LFL bridge (Magnit LFL vs X5 LFL, expansion-free) + M&A/expansion add-ons;
  quarterly-only expanding-window backtest (see skill_lfl.json); corrected FCFF engine (valuation.py).
No DDM: no predictable dividend policy and no sufficient FCF -> DDM weights REMOVED
(audit: weights without implementation). Revisit only with declared payout policy + coverage.
"""
ENGINE_VERSION = "magnit-v2"
# LFL nowcast bridge v2 (quarterly revenue-LFL yoy)
A_FOOD, B_PEER = 0.4, 0.6
SPREAD_RULE = "expanding-mean gap over prior quarterly origins (point-in-time, never current)"
# skill lives in data/skill_lfl.json (MAE/direction/coverage); constants must not duplicate it.
REGIME_PRIORS = {"stress": 1 / 6, "mid": 2 / 6, "healthy": 3 / 6}  # FY margin base-rate 2019-2025 (n=6)
REGIME_TILT = {"stress": 0.20, "mid": 0.42, "healthy": 0.38}  # judgment tilt (stated, NOT Bayes)
SHARES_ISSUED_M = 101.911355
SHARES_TREASURY_M = 34.064  # IFRS FY2025 note: own shares bought back
SHARES_OUTSTANDING_M = 67.847  # IFRS FY2025 circulation; T-Invest 67.871 stale -> use 67.847
# Canonical per-share basis = OUTSTANDING (ex-treasury): price discovery happens on tradeable
# shares; treasury economics accrue to remaining holders (cancel/sell/M&A/REPO optionality).
# Issued basis is shown only to reconcile MOEX-published cap (which overstates economic cap).
SHARES_CANONICAL_M = SHARES_OUTSTANDING_M
OUTSTANDING_FACTOR = SHARES_ISSUED_M / SHARES_OUTSTANDING_M  # 1.5021: issued-basis FV -> canonical
# treasury overhang scenarios (repo 3.817m pledged already): placement modeling must move
# BOTH shares and cash/net-debt. See dilution block in export_dashboard (computed, not static).
TREASURY_REPO_M = 3.817
# verified FY2025 anchors (bn rub unless noted)
FY2025 = {"revenue": 3509.2, "ebitda_pre16": 169.3, "ebitda_post16": 306.2,
          "net_debt_pre16": 496.3, "net_debt_post16": 1096.3, "leases": 600.1,
          "loans": 745.7, "capex_exMA": 187.1, "cost_of_debt_pct": 17.1,
          "da_rou": 159.4, "lease_cash_out": 57.0}
H1_2026 = {"revenue": 1887.2, "ebitda_pre16": 96.0, "ebitda_post16": 171.8,
           "ebitda_margin_pre16": 0.051, "net_debt_pre16": 518.1, "net_debt_post16": 1138.6,
           "capex_exMA": 36.8, "cost_of_debt_pct": 16.0, "net_loss": -1.9}
RECALIBRATION_TRIGGER = ">=12 quarterly LFL origins (have ~16 and growing), traffic-split bridge, M&A-quarter splits"
