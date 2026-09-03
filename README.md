# temp-zero-inode-850ms — Magnit FV dashboard

Live: https://tzi-850ms.pages.dev/ (Cloudflare Pages project `tzi-850ms`)

Static single-page dashboard (no deps, vanilla JS + SVG) fed by `web/data/data.json`,
exported from the Magnit FV model (`magnit/export_dashboard.py` in the model repo).

## Refresh (automatic)

Windows Task Scheduler on the model machine (times SGT = MSK+5):

| Task | When (SGT) | Does |
|---|---|---|
| MGNT-daily | 00:15 (= 19:15 MSK, post-close) | macro + market snapshot + report |
| MGNT-weekly | Mon 08:00 + Thu 04:00 (= Wed 23:00 MSK, post-Rosstat) | macro + market + X5 watcher + nowcast + report |
| MGNT-monthly | every 30 days 09:00 | full pipeline |

Dashboard `data.json` is re-exported + redeployed after each model refresh
(`export_dashboard.py` → `deploy.ps1`). Page header shows build time + MOEX update time.

## Manual refresh

```powershell
# 1. rebuild bundle
.venv\Scripts\python.exe 'C:\Users\rodio\Documents\Default Project\magnit\export_dashboard.py'
# 2. deploy
.\deploy.ps1 -Message "update YYYY-MM-DD"
```

Data: magnit.com IR (primary), Rosstat, CBR, x5.ru databook IAS17, MOEX ISS, T-invest.
Not investment advice — MOS/IRR/gates, no buy/sell labels.
