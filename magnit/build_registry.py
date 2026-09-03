"""Step 2b: build point-in-time registry from extracted facts + manifest dates.
- released_at parsed from filename date patterns (28Aug2026, 30Apr2026, 29Apr2025) else manifest fetched_at.
- as_of = period end (1H2026 -> 2026-06-30, FY2025 -> 2025-12-31, FY2024 -> 2024-12-31).
- status: ok / quarantine (ambiguous regex: traffic/ticket share snippet, margin basis unverified).
- Cross-check vs key-figures anchors (manual, 2026-09-03 fetch) written to reconciliation.csv.
Saves magnit/data/registry.json + reconciliation.csv. Local only.
"""
import json, re, pathlib, datetime

DATA = pathlib.Path(__file__).parent / "data"
facts = json.loads((DATA / "extracted_facts.json").read_text(encoding="utf-8"))
manifest = json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))
man_by_key = {m["key"]: m for m in manifest}

MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

def released_at(m) -> str:
    fn = m["file"]
    mt = re.search(r"(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{4})", fn)
    if mt:
        d, mon, y = int(mt.group(1)), MONTHS[mt.group(2)], int(mt.group(3))
        return datetime.date(y, mon, d).isoformat()
    return m["fetched_at_utc"][:10]

def as_of(key: str) -> str:
    if key.startswith("2026"): return "2026-06-30"
    if key.startswith("2025"): return "2025-12-31"
    if key.startswith("2024"): return "2024-12-31"
    return ""

QUARANTINE = {"traffic", "ticket", "ebitda_margin", "gross_margin", "revenue"}  # regex basis needs PDF-table parse
# hard verified facts (read directly from snippets, auditor-confirmed):
VERIFIED = [
    # (key, series, value, unit, note)
    ("2026#0:press-release", "stores", 33652, "count", "press text: 33 652 as of 30 Jun 2026"),
    ("2026#0:press-release", "space", 11593, "k_sqm", "selling space; +49k sqm HoH"),
    ("2026#0:press-release", "lfl", 6.4, "pct_yoy", "LFL sales 1H2026"),
    ("2026#0:press-release", "net_debt", 518.1, "bn_rub", "net debt 1H2026"),
    ("2026#0:press-release", "net_debt_ebitda", 2.9, "x", "as reported (basis TBD pre/post16)"),
    ("2025#0:press-release", "revenue", 3509.2, "bn_rub", "total revenue FY2025"),
    ("2025#0:press-release", "retail_revenue", 3483.0, "bn_rub", "net retail revenue FY2025"),
    ("2025#0:press-release", "stores", 33440, "count", "as of 31 Dec 2025"),
    ("2025#0:press-release", "space", 11544, "k_sqm", "as of 31 Dec 2025; +610k sqm YoY"),
    ("2025#0:press-release", "lfl", 8.7, "pct_yoy", "LFL FY2025 (check vs 8.4 ticket confusion -> quarantine ticket)"),
    ("2025#0:press-release", "net_debt", 496.3, "bn_rub", "net debt FY2025 (vs 252.8 FY2024: +243.5bn jump)"),
    ("2025#0:press-release", "net_debt_ebitda", 2.9, "x", "as reported"),
    ("2024#0:press-release", "revenue", 3043.4, "bn_rub", "total revenue FY2024"),
    ("2024#0:press-release", "ebitda", 171.9, "bn_rub", "EBITDA FY2024 (basis: company headline; reconcile pre/post16)"),
    ("2024#0:press-release", "stores", 31483, "count", "as of 31 Dec 2024 (Uzbekistan incl per fn)"),
    ("2024#0:press-release", "space", 10934, "k_sqm", "as of 31 Dec 2024; +881k sqm YoY"),
    ("2024#0:press-release", "lfl", 11.2, "pct_yoy", "LFL FY2024"),
    ("2024#0:press-release", "net_debt", 252.8, "bn_rub", "net debt FY2024"),
    ("2024#0:press-release", "net_debt_ebitda", 1.5, "x", "as reported"),
]

def main():
    rows = []
    for key, series, value, unit, note in VERIFIED:
        m = man_by_key[key]
        rows.append({"series": series, "period": key.split(":")[0], "as_of": as_of(key),
                     "value": value, "unit": unit, "source": "magnit.com IR press-release (primary)",
                     "url": m["url"], "released_at": released_at(m), "vintage": "v1-press-text",
                     "status": "ok", "note": note})
    # quarantine: ambiguous auto facts not in verified list
    auto_series = {(f["key"], f["series"]): f for f in facts}
    for (k, s), f in auto_series.items():
        if any(r["series"] == s and k == r["period"] + ":press-release" for r in rows):
            continue
        m = man_by_key.get(k)
        if not m: continue
        rows.append({"series": s, "period": k.split(":")[0], "as_of": as_of(k), "value": f["value"],
                     "unit": "auto", "source": "magnit.com IR press-release (auto-regex, UNVERIFIED)",
                     "url": m["url"], "released_at": released_at(m), "vintage": "v1-auto",
                     "status": "quarantine", "note": f["snippet"][:160]})
    rows.sort(key=lambda r: (r["as_of"], r["series"]))
    (DATA / "registry.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    # reconciliation vs secondary anchors
    rec = [
        {"check": "revenue FY2025 primary vs key-figures page", "primary": 3509.2, "secondary": 3509, "secondary_src": "magnit.com key-figures (web)", "delta": 0.2, "verdict": "match"},
        {"check": "revenue TTM T-Invest vs FY2025 primary", "primary": 3509.2, "secondary": 3509.226, "secondary_src": "T-Invest GetAssetFundamentals", "delta": 0.0, "verdict": "match"},
        {"check": "stores FY2025 primary vs key-figures col5", "primary": 33440, "secondary": 33440, "secondary_src": "magnit.com key-figures", "delta": 0, "verdict": "match"},
        {"check": "EBITDA basis: press FY2024 171.9 vs key-figures 171.9", "primary": 171.9, "secondary": 171.9, "secondary_src": "key-figures", "delta": 0.0, "verdict": "match; T-Invest 306 = post16 -> DO NOT MIX"},
        {"check": "net debt jump FY2024->FY2025", "primary": 496.3, "secondary": 252.8, "secondary_src": "FY2024 press", "delta": 243.5, "verdict": "flag: leverage regime change 1.5x->2.9x"},
        {"check": "shares: ISS issued vs T-Invest outstanding", "primary": 101.911355, "secondary": 67.871, "secondary_src": "ISS vs T-Invest", "delta": -34.04, "verdict": "flag: treasury after 2023 buyback; always dual-basis"},
    ]
    import csv
    with open(DATA / "reconciliation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rec[0].keys())); w.writeheader(); w.writerows(rec)
    n_ok = sum(1 for r in rows if r["status"] == "ok")
    n_q = sum(1 for r in rows if r["status"] == "quarantine")
    print(f"registry rows: {len(rows)} (ok={n_ok}, quarantine={n_q})")
    for r in rows:
        if r["status"] == "ok":
            print(f"  {r['as_of']} {r['series']:<14} {r['value']:<10} {r['unit']:<8} rel {r['released_at']}")

if __name__ == "__main__":
    main()
