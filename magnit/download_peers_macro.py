"""Download X5 peer PDFs + Rosstat weekly CPI XLSX (primary sources for nowcast leg).
Saves magnit/data/peers/ + magnit/data/macro/ + manifests with sha256.
"""
import hashlib, datetime, pathlib, urllib.request

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
BASE = pathlib.Path(__file__).parent / "data"

X5 = {
    # trading updates (lead Magnit by ~2-6 weeks) + financials
    "x5_q2_2026_trading": "https://www.x5.ru/wp-content/uploads/2026/07/q2_2026_trading_update_rus.pdf",
    "x5_q2_2026_fin": "https://www.x5.ru/wp-content/uploads/2026/08/x5_q2_2026_financial_results_rus.pdf",
    "x5_q1_2026_trading": "https://www.x5.ru/wp-content/uploads/2026/04/q1_2026_trading_update_rus.pdf",
    "x5_q1_2026_fin": "https://www.x5.ru/wp-content/uploads/2026/04/x5_q1_2026_financial_results_rus.pdf",
    "x5_q4_2025_trading": "https://www.x5.ru/wp-content/uploads/2026/01/q4_2025_trading_update_rus.pdf",
    "x5_q4_2025_fin": "https://www.x5.ru/wp-content/uploads/2026/03/x5_q4_2025_financial_results_rus.pdf",
    "x5_q4_2024_trading": "https://www.x5.ru/wp-content/uploads/2025/01/q4_2024_trading_update_rus.pdf",
    "x5_q4_2024_fin": "https://www.x5.ru/wp-content/uploads/2025/03/x5_q4_2024_financial_results_rus.pdf",
}
MACRO = {
    "rosstat_weekly_ipc": "https://rosstat.gov.ru/storage/mediabank/nedel_Ipc.xlsx",
    "rosstat_weekly_prices": "https://rosstat.gov.ru/storage/mediabank/nedel_sred_cen.xlsx",
    "rosstat_monthly_ipc": "https://rosstat.gov.ru/storage/mediabank/ipc_mes_07-2026.xlsx",
}

def dl(url, dest):
    req = urllib.request.Request(url, headers=H)
    data = urllib.request.urlopen(req, timeout=90).read()
    dest.write_bytes(data)
    return data

def main():
    out = []
    pd = BASE / "peers"; pd.mkdir(parents=True, exist_ok=True)
    for key, url in X5.items():
        dest = pd / (key + ".pdf")
        if dest.exists():
            print(f"HIT {key} ({dest.stat().st_size/1e3:.0f} KB)"); continue
        try:
            data = dl(url, dest)
            print(f"DL {key} ({len(data)/1e3:.0f} KB)")
        except Exception as e:
            print(f"FAIL {key}: {str(e)[:120]}"); continue
    md = BASE / "macro"; md.mkdir(parents=True, exist_ok=True)
    for key, url in MACRO.items():
        dest = md / (key + ".xlsx")
        try:
            data = dl(url, dest)
            sha = hashlib.sha256(data).hexdigest()
            out.append({"key": key, "url": url, "file": dest.name, "bytes": len(data),
                        "sha256": sha, "fetched_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
            print(f"DL {key} ({len(data)/1e3:.0f} KB, sha {sha[:12]})")
        except Exception as e:
            print(f"FAIL {key}: {str(e)[:150]}")
    (md / "manifest.json").write_text(__import__("json").dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    main()
