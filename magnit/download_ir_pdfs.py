"""Download full IR history: all results_years entries + archive 2019-2021 (press+presentation+accountability).
Idempotent via manifest keys. Quote URLs (spaces/Cyrillic).
"""
import json, hashlib, datetime, pathlib, urllib.request
from urllib.parse import urlsplit, urlunsplit, quote, unquote

BASE = "https://www.magnit.com"
D = pathlib.Path(__file__).parent / "data"
CAT = json.loads((D / "ir_catalog.json").read_text(encoding="utf-8"))
OUT = D / "pdfs"
OUT.mkdir(parents=True, exist_ok=True)

def q(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, quote(p.path), p.query, p.fragment))

def safe(link):
    name = unquote(link.split("/")[-1])
    return "".join(c if (c.isalnum() or c in "._- ()") else "_" for c in name)[:120]

def want():
    jobs = []
    for year, entries in CAT["results_years"].items():
        for i, e in enumerate(entries):
            for kind in ("press-release", "presentation", "accountability"):
                d = e.get(kind) or {}
                if d.get("link"):
                    jobs.append((f"{year}#{i}:{kind}", e.get("name", "")[:100], d["link"]))
    for year in ("2019", "2020", "2021"):
        for i, e in enumerate(CAT["archive"].get(year, [])):
            for kind in ("press-release", "presentation", "accountability"):
                d = e.get(kind) or {}
                if d.get("link"):
                    jobs.append((f"arc{year}#{i}:{kind}", e.get("name", "")[:100], d["link"]))
    return jobs

def main():
    import os
    man_path = OUT / "manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else []
    have = {m["key"]: m["file"] for m in manifest}
    # reconcile: files downloaded by killed run (key-prefixed names) without manifest entry
    by_file = {m["file"]: m for m in manifest}
    jobs = want()
    link_by_key = {k: (p, l) for k, p, l in jobs}
    filt = os.environ.get("IR_ONLY", "")
    n_new = 0
    for f in sorted(OUT.glob("*.pdf")):
        if f.name in by_file: continue
        # filename = key(with _ for # and :)_safe-name
        for key in link_by_key:
            prefix = key.replace("#", "_").replace(":", "_") + "_"
            if f.name.startswith(prefix):
                period, link = link_by_key[key]
                data = f.read_bytes()
                manifest.append({"key": key, "period": period, "kind": key.split(":")[1],
                                 "url": BASE + link, "file": f.name, "bytes": len(data),
                                 "sha256": hashlib.sha256(data).hexdigest(),
                                 "fetched_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
                have[key] = f.name
                n_new += 1
                break
    if n_new:
        man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"reconciled {n_new} orphan files")
    dl_n = 0
    for key, period, link in jobs:
        if filt and not key.startswith(filt): continue
        if key in have and (OUT / have[key]).exists():
            continue
        url = BASE + link
        fname = f"{key.replace('#','_').replace(':','_')}_{safe(link)}"
        try:
            req = urllib.request.Request(q(url), headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=120).read()
            (OUT / fname).write_bytes(data)
            manifest.append({"key": key, "period": period, "kind": key.split(":")[1], "url": url,
                             "file": fname, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                             "fetched_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
            man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
            have[key] = fname
            dl_n += 1
            print(f"DL {key} ({len(data)/1e6:.2f} MB)", flush=True)
        except Exception as e:
            print(f"FAIL {key}: {str(e)[:130]}", flush=True)
    print(f"downloaded {dl_n}; manifest {len(manifest)}")

if __name__ == "__main__":
    main()
