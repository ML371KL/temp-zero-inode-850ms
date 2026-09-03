"""X5 update watcher: scans x5.ru results page for NEW trading/financial PDFs + databook.
Compares against data/peers/x5_seen.json; downloads new files; appends alerts.
Idempotent. Exit 0 always (watcher is non-critical); findings in x5_watcher.json.
--seed: record current page state without downloading (first run against full archive).
--since YYYY-MM-DD: only download docs newer than date (from URL/upload path year-month).
"""
import urllib.request, re, json, pathlib, datetime, sys

D = pathlib.Path(__file__).parent / "data" / "peers"
SEED_ONLY = "--seed" in sys.argv
SEEN = D / "x5_seen.json"
OUT = D / "x5_watcher.json"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
PAGE = "https://www.x5.ru/ru/investors/financial-and-operational-results/"

def main():
    seen = json.loads(SEEN.read_text(encoding="utf-8")) if SEEN.exists() else {"urls": [], "checked_utc": None}
    try:
        t = urllib.request.urlopen(urllib.request.Request(PAGE, headers=H), timeout=40).read().decode("utf-8", "ignore")
    except Exception as e:
        OUT.write_text(json.dumps({"checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                   "status": "fetch_failed", "error": repr(e)[:200]}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("watcher: page fetch failed"); return 0
    links = sorted(set(re.findall(r'href="(https://www\.x5\.ru/wp-content/uploads/[^"]+\.(?:pdf|xlsx))"', t)))
    known = set(seen["urls"])
    new = [u for u in links if u not in known]
    # filter to investor-relevant docs only
    rel = [u for u in new if re.search(r"trading_update|financial_results|financial_and_operating|investor_day|presentation", u, re.I)]
    got, failed = [], []
    if SEED_ONLY:
        print(f"seed: recording {len(links)} links, no downloads")
    else:
        for u in rel:
            fn = u.split("/")[-1]
            dest = D / fn
            if dest.exists():
                got.append(fn); continue
            try:
                dest.write_bytes(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=120).read())
                got.append(fn)
            except Exception as e:
                failed.append({"url": u, "error": repr(e)[:150]})
    seen["urls"] = sorted(known | set(links))
    seen["checked_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    SEEN.write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")
    alerts = []
    for fn in got:
        if re.search(r"q3_2026|Q3.*2026|3кв.*2026", fn, re.I): alerts.append(f"X5 Q3 2026 just dropped: {fn} -> rerun nowcast with ACTUAL (replaces carry)")
        elif re.search(r"trading_update", fn, re.I): alerts.append(f"new X5 trading update: {fn}")
        elif re.search(r"financial_results", fn, re.I): alerts.append(f"new X5 financials: {fn}")
        elif re.search(r"financial_and_operating", fn, re.I): alerts.append(f"new X5 databook: {fn} -> rerun parse_x5_book")
    OUT.write_text(json.dumps({"checked_utc": seen["checked_utc"], "status": "ok",
                               "new_relevant": rel, "downloaded": got, "failed": failed, "alerts": alerts},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"watcher: {len(links)} links, {len(rel)} new relevant, alerts={len(alerts)}")
    for a in alerts: print(" ALERT:", a)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
