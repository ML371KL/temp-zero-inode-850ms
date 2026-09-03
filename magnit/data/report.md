# Magnit FV report (2026-09-03, local)

Market: **1589** (issued cap 161.9bn / outst 107.8bn) | MOEX update: 18:06:26

FV posterior (outstanding 67.8m (canonical)): mean **4993** | p05 45 p25 1718 p50 3468 p75 8960 p95 11303 | P(FV>P)=76.9%

Gates: E[IRR(2y)]>=25% + P>=0.5 + leverage falling 2Q + cod falling. Leverage gate: ND/EBITDA pre16 H1 = 2.9x (flat) -> BLOCKS. cod 14.03% WACC 14.11% (key 14.0%).

Bridge skill: MAE 5.65pp (naive-X5 10.63pp), direction 7/14, bias -0.36pp. LFL-bridge v2 (ma_layer) preferred structurally.

Credit: net 518.1bn pre16; cash/short 1.53x; undrawn 606.2bn; covenants complied; risk = carry, not solvency.

Alerts:

- VALUE: P(FV>P)=77% with E[FV]=4993.0

Robustness (sensitivity audit, canonical basis): single-factor bears hold above (bear-probs 2420, mult -0.5x 2707, debt +60bn 2755); only the joint bear combo (stress-heavy + WACC +2pp + mult -0.5x + debt +60bn) breaks below at 208. Price 1580 sits below the posterior bulk but the left tail is real (p05 45): WAIT is the robust middle — action only when leverage/cod gates resolve the uncertainty.


Next catalysts: X5 Q3 trading (~14 Oct, lead 2-6 wks) -> Magnit Q3/LFL; CBR meetings -> WACC; Q3 ND/EBITDA.

Live nowcast (2026-09-03): Magnit Q3 2026 LFL yoy = **7.09%** (food 5.03% + carry Q2 (rel 16Jul2026); X5 Q3 trading ~14Oct). Q3 LFL nowcast 7.09% vs H1 6.4% / Q2-impl ~6.3%: stable.
  - nowcast caveat: Q3-2026 index partial (1/3 months: official m/m through Jul only + weekly shape)
  - nowcast caveat: Sep weekly points: 0