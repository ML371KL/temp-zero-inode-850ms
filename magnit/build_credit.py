"""Credit profile from IFRS primary texts (FY2025 + 1H2026). All figures bn rub.
Saves magnit/data/credit.json
"""
import json, pathlib

credit = {
    "as_of": "2026-06-30",
    "loans": {"long": 658.9, "short": 263.3, "total": 922.2,
              "prev_2025": {"long": 467.8, "short": 277.9, "total": 745.8},
              "note": "H1 long +191bn; ST -14.6bn"},
    "cash": {"h1_2026": 404.1, "ye2025": 244.5, "note": "prefunding build +160bn; IFRS balance sheet"},
    "net_debt_pre16": {"h1_2026": 518.1, "ye2025": 496.3,
                       "check": "922.2-404.1=518.1 EXACT vs press; 745.8-244.5=501.3 vs press 496.3 (delta 5.0: def. cash equiv.)"},
    "leases_post16_gap": 600.1,
    "hidden": {"dv_nevada_put": 26.6, "put_note": "call/put to 31 Oct 2029; +2.0bn H1 accretion; add to adjusted debt",
               "repo_treasury": 3.0, "repo_note": "3.8m treasury shares pledged; FV 6.7bn at Jun-26 (price-implied ~1767)"},
    "liquidity": {"cash_to_short": round(404.1 / 263.3, 2), "undrawn_lines": 606.2,
                  "bonds": "unsecured 2027-2034 (termed out, no imminent wall)",
                  "covenants": "complied 31Dec2025 + 30Jun2026"},
    "flow_2025": {"raised": 701.3, "repaid": 373.6, "lease_paid": 57.0, "note": "refi wave; H2 borrowings to refinance 2026 maturities (press)"},
    "conclusion": "Solvency risk LOW (cash+lines cover ST 3.8x; wall termed to 2027+); risk is CARRY (16% on gross 922) dragging net income, not default. Leverage gate in decision layer should track NET debt/EBITDA + cod, not gross.",
    "open_item": "maturity-bucket table (note 33) not machine-parsed (variable group widths); read manually for exact 12m wall",
}
pathlib.Path("magnit/data/credit.json").write_text(json.dumps(credit, ensure_ascii=False, indent=1), encoding="utf-8")
print("cash/ST:", credit["liquidity"]["cash_to_short"], "| net debt check:", credit["net_debt_pre16"]["check"][:60])
print("saved credit.json")
