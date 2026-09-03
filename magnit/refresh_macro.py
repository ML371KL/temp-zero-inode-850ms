"""Macro refresh wrapper: Rosstat weekly+monthly CPI, CBR key rate, WACC bridge.
Each step is idempotent (re-download + reparse). Non-critical failures degrade to previous files.
"""
import subprocess, sys, pathlib

REPO_ROOT = str(pathlib.Path(__file__).parent.parent)

STEPS = [
    ("rosstat_weekly", [sys.executable, "magnit/download_peers_macro.py"]),  # re-fetches XLSX (cheap)
    ("parse_food_weekly", [sys.executable, "magnit/parse_rosstat_weekly.py"]),
    ("parse_food_monthly", [sys.executable, "magnit/parse_rosstat_monthly.py"]),
    ("cbr", [sys.executable, "magnit/fetch_cbr.py"]),
    ("wacc", [sys.executable, "magnit/wacc_bridge.py"]),
]
rc = 0
for name, cmd in STEPS:
    r = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=600)
    print(f"[{name}] rc={r.returncode}")
    if r.returncode != 0:
        print((r.stdout or "")[-500:]); print((r.stderr or "")[-500:])
        rc = 1
        break
sys.exit(rc)
