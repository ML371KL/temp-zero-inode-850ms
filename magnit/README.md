# Magnit FV model (local prototype, no deploy)

Dynamic fair-value model for PAO Magnit (MGNT): real-time market snapshot,
primary-source fundamentals (magnit.com IR), peer/macro nowcast bridge,
hybrid valuation as a **distribution**, decision gates (no buy/sell labels).

## Verdict (2026-09-03, issued-share basis)

- Market 1580 (cap 161.4bn issued / 107.4bn outstanding).
- FV posterior: mean 3324 | p05 30 p25 1144 **p50 2309** p75 5965 p95 7525 | P(FV>P)=65%.
- Gates 3/4 → **WAIT** (leverage gate blocks: ND/EBITDA 2.9x flat; cod falling 17.1→16.0).
- Live: Q3 LFL nowcast 7.09% vs H1 6.4% (partial data, see caveats).
- Full text: `data/report.md`.

## Architecture

```
IR catalog → PDFs → parse (P&L/LFL/IFRS) → registry (point-in-time, upsert, vintage log)
Macro (Rosstat weekly+monthly CPI, CBR key rate → WACC) + Peers (X5 databook IAS17, Lenta thin)
  → nowcast bridges (revenue v1: MAE 5.65pp; LFL v2 structural) + M&A add-on layer
  → hybrid EV blend (DCF floored at 0, distress = mult-only) → FV distribution (50k draws)
  → decision gates → report.md + alerts.json
```

Key findings baked in: shares 101.911m issued / 67.847m outstanding (treasury 34.064m, IFRS);
pre/post-IFRS16 never mixed (lease gap 600.1bn reconciled); spot FCF<0 → normalized FCF;
organic convergence vs X5 (−8.6→−0.2pp); credit = carry risk, not solvency (cash/ST 1.5x,
undrawn 606bn, bonds termed 2027–2034, covenants complied).

## Data map (primary unless noted)

| Input | Source | Freshness |
|---|---|---|
| IR reports (80 PDFs, 2019–2026) | magnit.com IR catalog | on release |
| Revenue/P&L/LFL/debt | press releases + IFRS statements | on release |
| Weekly/monthly food CPI | Rosstat mediabank XLSX | weekly Wed |
| Key rate → cod → WACC | cbr.ru KeyRate + reported cod | on decision |
| X5 revenue/margins/LFL IAS17 | x5.ru databook XLSX | quarterly |
| Lenta (thin, secondary) | T-invest API | snapshot |
| Price/cap/fundamentals/consensus | MOEX ISS + T-invest API | daily |
| Order book (Algopack) | PARKED — subscribers-only, adds nothing at this horizon | — |
| e-disclosure mirror | BLOCKED (JS challenge; method in fetch_edisclosure.py) | — |

## Dashboard (live)

https://tzi-850ms.pages.dev/ — Cloudflare Pages (`tzi-850ms`), repo
https://github.com/ML371KL/temp-zero-inode-850ms. Static UI + `data.json` bundle;
refresh = `magnit/export_dashboard.py` → `deploy.ps1` in the dashboard repo.

## Runbook (local only)

```powershell
.venv\Scripts\python.exe -m pytest magnit\tests -q   # 10 invariants, fail-closed
.venv\Scripts\python.exe magnit\refresh.py --dry-run # orchestration check
.venv\Scripts\python.exe magnit\scheduled.py weekly  # macro+market+nowcast+report
.venv\Scripts\python.exe magnit\scheduled.py daily   # market+report
```

Scheduler (one-time, elevated PowerShell): `magnit\register_scheduler.ps1`.
Artifacts: `data/report.md`, `data/alerts.json`, `data/market/latest.json`,
`data/fv_dist.json`, `data/vintages/`, `data/runs/`.

## Rules

- Point-in-time or fail closed; red runs never touch last-good outputs.
- Frozen calibration changes only via recalibration trigger (constants.py).
- Dual share basis + single EBITDA/debt basis stated on every output.
- Quarantine, don't silently drop; identity checks decide (LFL=ticket×traffic, margins).
- No buy/sell labels — MOS/IRR/gates only.

## Known gaps (next)

X5 Q3 trading (~14 Oct) = first live nowcast-vs-actual test; note-33 maturity buckets
(manual read); e-disclosure via browser; Dixy quarterly splits (banded); dashboard deploy
(explicitly out of scope for now).
