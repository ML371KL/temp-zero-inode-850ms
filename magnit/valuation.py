"""Shared valuation math — single source of truth for fv_distribution and sensitivity_audit.

Corrected FCFF (pre-IFRS16, post audit 2026-09-04):
  FCFF = EBITDA - cash_taxes_on_EBIT - capex_total - dNWC        (NO interest: interest is debtholder flow)
  cash_taxes_on_EBIT = max(0, EBITDA - DA) * TAX
  DA_RATE = 0.028  (FY2025: (169.3-70.5)/3509.2 = 2.82%; H1 2026 ~2.5%; IFRS16 bridge caveat noted)
  capex_total = capex_maint + capex_growth
  capex_maint = MAINT_RATE * rev  (MAINT_RATE = 0.028 ~ D&A steady state)
  capex_growth = max(0, g_explicit) * rev * CAPEX_GROWTH_INTENSITY (0.35, stated prior)
  dNWC_norm = WC_INTENSITY * rev * g_norm  (WC_INTENSITY = 0.12 stated prior; NWC-model roadmap)
Equity = max(0, EV_hybrid - net_debt - other_claims); distress regimes use mult-only EV.
"""
from __future__ import annotations

TAX = 0.25
DA_RATE = 0.028
MAINT_RATE = 0.028
CAPEX_GROWTH_INTENSITY = 0.35
WC_INTENSITY = 0.12
G_EXPLICIT = 0.04
G_TERMINAL = 0.03
T_EXPLICIT = 5


def build_fcf(ebitda: float, rev: float, capex_growth_extra: float = 0.0,
              dwc_extra: float = 0.0) -> dict:
    """Normalized one-year FCFF from operating inputs. Returns components for audit."""
    da = DA_RATE * rev
    ebit = ebitda - da
    tax = max(0.0, ebit) * TAX
    capex_maint = MAINT_RATE * rev
    capex_growth = max(0.0, G_EXPLICIT) * rev * CAPEX_GROWTH_INTENSITY + capex_growth_extra
    dwc = WC_INTENSITY * rev * G_EXPLICIT + dwc_extra
    fcf = ebitda - tax - (capex_maint + capex_growth) - dwc
    return {"fcf": fcf, "da": da, "ebit": ebit, "tax": tax,
            "capex_maint": capex_maint, "capex_growth": capex_growth, "dwc": dwc}


def dcf_ev(fcf0: float, wacc: float, g: float = G_TERMINAL,
           years: int = T_EXPLICIT, gg: float = G_EXPLICIT) -> dict:
    """Two-stage DCF on FCFF. Returns EV + explicit/terminal split (for terminal-share metric)."""
    if wacc <= g:
        raise ValueError("wacc must exceed g")
    pv, f = 0.0, fcf0
    for t in range(1, years + 1):
        f *= (1 + gg)
        pv += f / ((1 + wacc) ** t)
    tv = f * (1 + g) / (wacc - g) / ((1 + wacc) ** years)
    return {"ev": pv + tv, "explicit": pv, "terminal": tv,
            "terminal_share": tv / (pv + tv) if (pv + tv) > 0 else 0.0}


def blend_ev(ev_dcf: float, ev_mult: float, w_dcf: float) -> float:
    """Single weight + complement. w_dcf in [0,1]; mult leg ALWAYS gets (1-w_dcf)."""
    assert 0.0 <= w_dcf <= 1.0, w_dcf
    return w_dcf * max(0.0, ev_dcf) + (1 - w_dcf) * ev_mult
