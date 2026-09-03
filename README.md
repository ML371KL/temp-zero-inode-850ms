# temp-zero-inode-850ms — Magnit FV dashboard

Live: https://tzi-850ms.pages.dev/ (Cloudflare Pages project `tzi-850ms`)

Static single-page dashboard (no deps, vanilla JS + SVG) fed by `web/data/data.json`,
exported from the Magnit FV model (`magnit/export_dashboard.py` in the model repo).

## Refresh

```powershell
# 1. rebuild bundle
.venv\Scripts\python.exe 'C:\Users\rodio\Documents\Default Project\magnit\export_dashboard.py'
# 2. deploy
.\deploy.ps1 -Message "update YYYY-MM-DD"
```

Data: magnit.com IR (primary), Rosstat, CBR, x5.ru databook IAS17, MOEX ISS, T-invest.
Not investment advice — MOS/IRR/gates, no buy/sell labels.
