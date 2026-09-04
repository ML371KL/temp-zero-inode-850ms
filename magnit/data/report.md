# Magnit FV report (2026-09-04, local)

Market: **1581** (issued cap 161.1bn / outst 107.3bn) | MOEX update: 18:49:52

FV mix (outstanding 67.8m (canonical)): mean **2439** | p05 0 p25 371 p50 1478 p75 4656 p95 6419 | P(FV>P)=48.2%

TSR_2y (full draws): median -6.6% mean 54.3% | P(hurdle 25pa)=40.0% P(loss30)=42.8% P(loss50)=35.4% CVaR5=-100.0% | p25 MOS=-76.5%.

Gates: p_hurdle_ge_50 BLOCKS · leverage_below_2_5x BLOCKS · cod_falling PASS -> **WAIT** (leverage {'2020FY': 1.24, '2021H1': 1.18, '2021FY': 1.48, '2022H1': 1.18, '2022FY': 0.7, '2023H1': 0.72, '2023FY': 1.0, '2024H1': 1.37, '2024FY': 1.47, '2025H1': 2.39, '2025FY': 2.93, '2026H1': 2.88} | cod [17.1, 16.0]).

cod 14.03% WACC 14.11% (key 14.0%).

Bridge skill (LFL quarterly-only, expanding window): MAE 4.02pp, direction 7/15 (coin flip: levels only, no turning-point skill), interval coverage 0.562. Naive-X5 MAE ?pp where available.

Credit: net 518.1bn pre16; cash/short 1.53x; undrawn 606.2bn; covenants complied. Near-term liquidity looks sufficient; mid-term refinancing + interest carry remain the material equity risk (maturity-bucket table unparsed: see credit.open_item).

Alerts:
- none

Robustness (sensitivity.json, canonical basis): base: median 1511 (overlap); bear_probs: median 1034 (overlap); bull_probs: median 2975 (above); wacc_up_2pp: median 1426 (overlap); wacc_down_2pp: median 1656 (overlap); mult_down_0_5x: median 468 (overlap); mult_up_0_5x: median 2593 (above); debt_up_60bn: median 627 (overlap); debt_down_60bn: median 2396 (above); bear_combo: median 0 (below); bull_combo: median 5232 (above). Price 1581 vs mix p05 0.0 / p95 6419.0: value is uncertain, not cheap; WAIT is the robust middle until gates resolve.


Next catalysts: X5 Q3 trading (~14 Oct, lead 2-6 wks) -> Magnit Q3/LFL; CBR meetings -> WACC; Q3 ND/EBITDA.

Live nowcast (2026-09-04): Magnit Q3 2026 LFL yoy = **-2%** (food 4.4% + carry Q2 (rel 16Jul2026); X5 Q3 trading ~14Oct; carry widens interval). preliminary Q3 LFL bridge: about -2%, low confidence (±4.02pp backtest interval).
  - nowcast caveat: food index partial (1/3 months of Q3; symmetric month-vs-month only)
  - nowcast caveat: no September weekly points yet (file through Aug-31)