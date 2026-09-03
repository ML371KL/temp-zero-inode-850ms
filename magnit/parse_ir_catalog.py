"""Step 1: parse magnit.com IR catalog (primary source) from embedded JSON blob.
Reads live page (or cached HTML), extracts structured catalog:
  year -> [{name, presentation:{link,size}, press-release:{...}, accountability:{...}}]
Saves magnit/data/ir_catalog.json + ir_catalog_meta.json (fetched_at, sha256, url).
No secrets. Local only.
"""
import re, json, hashlib, datetime, pathlib, urllib.request

BASE = "https://www.magnit.com"
URL = "https://www.magnit.com/ru/shareholders-and-investors/results-and-reports/"
OUT_DIR = pathlib.Path(__file__).parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def fetch_html(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    return urllib.request.urlopen(req, timeout=30).read()

def extract_reports_json_lenient(raw: str) -> dict:
    """Parse the embedded JSON object after '"reports-and-results-list":' with a real
    JSON decoder (brace-counting breaks on braces inside strings)."""
    import json as _json
    key = '"reports-and-results-list":'
    i = raw.find(key)
    assert i != -1, "catalog marker not found"
    j = raw.find("{", i + len(key))
    dec = _json.JSONDecoder()
    obj, _ = dec.raw_decode(raw[j:])
    return obj

def main():
    raw_bytes = fetch_html(URL)
    sha = hashlib.sha256(raw_bytes).hexdigest()
    raw = raw_bytes.decode("utf-8", errors="ignore")
    blob = extract_reports_json_lenient(raw)
    # blob = {"results": {"years": {...}, "archive": {...}}, "reports": [...], "documents": ...}
    res = blob.get("results", {})
    catalog = {"results_years": res.get("years", {}),
               "archive": res.get("archive", {})}
    # normalize links: \\/ -> /
    norm = json.loads(json.dumps(catalog).replace("\\/", "/"))
    # stats
    n_periods = sum(len(v) for v in norm["results_years"].values()) if isinstance(norm["results_years"], dict) else 0
    pdfs = set(re.findall(r"/upload/iblock/.*?\.pdf", json.dumps(norm)))
    # fix escaped unicode leftovers already decoded by json
    meta = {"source_url": URL,
            "fetched_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "html_sha256": sha,
            "n_periods_results": n_periods,
            "n_pdf_links": len(pdfs),
            "archive_years": sorted(norm["archive"].keys()) if isinstance(norm["archive"], dict) else []}
    (OUT_DIR / "ir_catalog.json").write_text(json.dumps(norm, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / "ir_catalog_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"periods(results)={n_periods} pdfs={len(pdfs)} archive_years={meta['archive_years'][:5]}... total={len(meta['archive_years'])}")
    # show latest year entries
    years = sorted(norm["results_years"].keys(), reverse=True)[:3]
    for y in years:
        print(f"== {y} ==")
        for e in norm["results_years"][y][:4]:
            pr = (e.get("press-release") or {})
            pres = (e.get("presentation") or {})
            acc = (e.get("accountability") or {})
            name = e.get("name", "")[:80]
            print(" -", name.encode("ascii", "backslashreplace").decode())
            print("    PR:", pr.get("link", ""))
            print("    PRES:", pres.get("link", ""))
            print("    ACC:", (acc or {}).get("link", "") if isinstance(acc, dict) else "")

if __name__ == "__main__":
    main()
