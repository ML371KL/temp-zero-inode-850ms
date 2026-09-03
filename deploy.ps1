# Refresh + deploy (local, manual cadence until GH integration).
# 1) Rebuild bundle from model:  .venv\Scripts\python.exe C:\Users\rodio\Documents\'Default Project'\magnit\export_dashboard.py
# 2) Deploy:                     .\deploy.ps1 -Message "update <date>"
param([string]$Message = "dashboard update")
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
& "C:\Program Files\nodejs\npx.cmd" -y wrangler@4.26.0 pages deploy web --project-name tzi-850ms --branch main --commit-message $Message
Write-Output "live: https://tzi-850ms.pages.dev/"
