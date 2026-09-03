"""Magnit fair-value prototype (local only, no network publish).

Design (aligned with user answers):
- FV as distribution, invariant to horizon in theory; horizon enters only via
  (a) explicit forecast length and (b) decision rule (margin of safety / annualization).
- Hybrid triangulation with regime-dependent weights:
  w_dcf falls when leverage (NetDebt/EBITDA) is high; w_mult rises; w_ddm only if dividends resumed.
- Point-in-time: every input carries (as_of, released_at, vintage); nowcast bridge
  never rewrites a published quarter, it only produces a pre-report estimate.
- Primary sources first: magnit.com /upload/iblock catalog (530 PDFs found 2026-09-03),
  e-disclosure id=7671; SmartLab/MOEX/T-Invest are secondary/market layers.

Accounting identity (retail, pre-IFRS16 vs post-IFRS16 kept separate):
  Revenue = Stores * SalesPerStore  (= Traffic * Ticket, LFL split)
  GrossProfit = Revenue * GrossMargin
  EBITDA(pre16) = GrossProfit - SGA_excl_rent - ...
  EBITDA(post16) = EBITDA(pre16) + Rent (lease add-back)  ~ ratio observed 306/169 = 1.81x
  EBIT = EBITDA - D&A ;  NetIncome = EBIT - Interest - Tax
  FCF = EBITDA - Tax_paid - Interest_paid - Capex - dWC
  EV = Equity + NetDebt (incl. leases iff EBITDA post16); P = (EV - NetDebt)/Shares
Shares: ISSUED=101.911355m (ISS) vs OUTSTANDING~67.9m (T-Invest, ex-treasury after 2023 buyback).
Engine always outputs BOTH per-share bases and flags the denominator.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

ISSUED_M = 101.911355
OUTSTANDING_M = 67.847  # IFRS FY2025 note: 101.911 - 34.064 treasury (T-invest 67.871 stale)
RENT_MULT_OBSERVED = 306.162 / 169.3  # post16/pre16 EBITDA 2024-25TTM mix; must be estimated per period, not frozen

@dataclass
class OperatingCase:
    name: str
    revenue_bn: float
    ebitda_pre16_bn: float
    net_debt_pre16_bn: float  # ex-leases
    lease_liab_bn: float = 0.0
    capex_bn: float = 150.0
    tax_rate: float = 0.25
    interest_bn: float = 60.0  # annual; scaled by key rate in full model
    dwc_bn: float = 10.0

    @property
    def ebitda_margin(self): return self.ebitda_pre16_bn / self.revenue_bn
    @property
    def net_debt_post16(self): return self.net_debt_pre16_bn + self.lease_liab_bn
    @property
    def ebitda_post16(self): return self.ebitda_pre16_bn * RENT_MULT_OBSERVED
    @property
    def leverage_pre16(self): return self.net_debt_pre16_bn / self.ebitda_pre16_bn
    @property
    def fcf_pre16(self):
        # simplified cash conversion: EBITDA - tax on EBIT proxy - interest - capex - dWC
        # D&A proxy 4% of revenue (Magnit 2022-24 ~3.5-4.5%); EBIT = EBITDA - DA
        da = 0.04 * self.revenue_bn
        ebit = self.ebitda_pre16_bn - da
        tax = max(0.0, ebit - self.interest_bn) * self.tax_rate
        return self.ebitda_pre16_bn - tax - self.interest_bn - self.capex_bn - self.dwc_bn

def regime_weights(leverage: float):
    """Hybrid weights as function of stress. Calibrated qualitatively; must be frozen
    via backtest before production (cf. 842 constants.py rule).
    In distress blend on EV (not equity) to avoid double-subtracting debt."""
    if leverage >= 2.5:   # distress: DCF on spot FCF unreliable
        return {"dcf": 0.25, "mult": 0.75, "ddm": 0.0, "blend_on": "EV"}
    if leverage >= 1.5:
        return {"dcf": 0.45, "mult": 0.40, "ddm": 0.15, "blend_on": "equity"}
    return {"dcf": 0.55, "mult": 0.30, "ddm": 0.15, "blend_on": "equity"}

def dcf_ev_bn(fcf0: float, wacc: float, g: float, years_explicit: int = 5, growth_explicit: float = 0.04):
    """Enterprise value (before debt). Equity = EV - NetDebt, floored at 0 (option framing)."""
    if wacc <= g: raise ValueError("wacc must exceed g")
    pv = 0.0
    f = fcf0
    for t in range(1, years_explicit + 1):
        f *= (1 + growth_explicit)
        pv += f / ((1 + wacc) ** t)
    terminal = f * (1 + g) / (wacc - g) / ((1 + wacc) ** years_explicit)
    return pv + terminal

def dcf_equity_bn(fcf0: float, wacc: float, g: float, net_debt: float, years_explicit: int = 5, growth_explicit: float = 0.04):
    """Two-stage DCF on normalized (not spot) FCF. Returns equity value."""
    if wacc <= g: raise ValueError("wacc must exceed g")
    pv = 0.0
    f = fcf0
    for t in range(1, years_explicit + 1):
        f *= (1 + growth_explicit)
        pv += f / ((1 + wacc) ** t)
    terminal = f * (1 + g) / (wacc - g) / ((1 + wacc) ** years_explicit)
    return pv + terminal - net_debt

def mult_equity_bn(ebitda: float, ev_ebitda: float, net_debt_same_basis: float):
    return ebitda * ev_ebitda - net_debt_same_basis

def per_share(equity_bn: float, shares_m: float): return equity_bn * 1000.0 / shares_m

def nowcast_revenue_bridge(prior_rev: float, food_cpi_yoy: float, peers_rev_yoy: float, traffic_proxy: float,
                            w_cpi=0.35, w_peer=0.45, w_traf=0.20):
    """DEPRECATED v0 stub (kept for run_prototype.py snapshot). Use track_skill.py
    (v1 revenue bridge, MAE 5.65pp) and ma_layer.py (v2 LFL bridge) instead.
    Returns (nowcast, contribution dict)."""
    assert abs(w_cpi + w_peer + w_traf - 1.0) < 1e-9
    g = w_cpi * food_cpi_yoy + w_peer * peers_rev_yoy + w_traf * traffic_proxy
    return prior_rev * (1 + g), {"cpi": w_cpi * food_cpi_yoy, "peer": w_peer * peers_rev_yoy, "traf": w_traf * traffic_proxy, "g": g}
