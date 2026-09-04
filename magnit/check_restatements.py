"""Restatement detector (monthly): re-fetch IR catalog, compare PDF set + hashes.
- New URLs -> new documents (info event, not restatement).
- Same URL, hash changed (HEAD size mismatch -> GET + sha256) -> RESTATEMENT:
  affected registry rows get superseded copies with restatement_id (old rows kept!).
- Writes data/restatements.json + appends superseding rows to registry.
Never deletes. Exit 0 always (non-critical stage).
"""
import urllib.request, json, pathlib, datetime, hashlib
from urllib.parse import urlsplit, urlunsplit, quote

BASE = pathlib.Path(__file__).parent / "data"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
MGNT = "https://www.magnit.com"


def q(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, quote(p.path), p.query, p.fragment))


def head_size(url):
    req = urllib.request.Request(q(url), headers=H, method="HEAD")
    try:
        r = urllib.request.urlopen(req, timeout=30)
        v = r.headers.get("Content-Length")
        return int(v) if v else None
    except Exception:
        return None


def main():
    manifest = json.loads((BASE / "pdfs" / "manifest.json").read_text(encoding="utf-8"))
    by_url = {m["url"]: m for m in manifest}
    reg = json.loads((BASE / "registry.json").read_text(encoding="utf-8"))
    # catalog re-fetch (reuse parser)
    import sys
    sys.path.insert(0, str(BASE.parent))
    out = {"checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "new_docs": [], "restatements": []}
    # collect current catalog links
    try:
        req = urllib.request.Request("https://www.magnit.com/ru/shareholders-and-investors/results-and-reports/", headers=H)
        raw = urllib.request.urlopen(req, timeout=40).read()
        import re
        links = sorted(set(re.findall(rb"/upload/iblock/[^\"'\\s]+\.pdf", raw)))
        links = [MGNT + l.decode("utf-8", "ignore") for l in links]
    except Exception as e:
        out["status"] = f"catalog fetch failed: {e!r}"[:200]
        (BASE / "restatements.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("catalog fetch failed"); return 0
    known_urls = set(by_url)
    for u in links:
        if u not in known_urls:
            out["new_docs"].append(u)
    # restatement check on tracked press/accountability PDFs only (skip presentations: big, low value)
    tracked = [m for m in manifest if m["kind"] in ("press-release", "accountability")]
    for m in tracked:
        sz = head_size(m["url"])
        if sz is not None and sz == m.get("bytes"):
            continue
        # size unknown or changed -> download + hash
        try:
            data = urllib.request.urlopen(urllib.request.Request(q(m["url"]), headers=H), timeout=120).read()
        except Exception as e:
            out.setdefault("fetch_errors", []).append({"url": m["url"], "error": repr(e)[:150]})
            continue
        sha = hashlib.sha256(data).hexdigest()
        if sha != m.get("sha256"):
            rid = f"R-{datetime.date.today().isoformat()}-{sha[:8]}"
            out["restatements"].append({"url": m["url"], "old_sha": m.get("sha256"),
                                        "new_sha": sha, "restatement_id": rid, "key": m["key"]})
            m["sha256"], m["bytes"] = sha, len(data)
            # supersede affected rows (keep old!)
            for x in reg:
                if x.get("url") == m["url"] and x.get("status") == "ok" and not x.get("supersedes"):
                    x["status"] = "superseded"
                    y = dict(x, status="quarantine", supersedes=(x.get("vintage_id"), x["value"]),
                             restatement_id=rid,
                             note=x.get("note", "") + f" [UNDER REVIEW post-{rid}: source hash changed; re-parse pending]")
                    reg.append(y)
    (BASE / "pdfs" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    reg.sort(key=lambda r: (r["as_of"], r["series"]))
    (BASE / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    out["status"] = "ok"
    (BASE / "restatements.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"checked {len(tracked)} tracked PDFs: {len(out['new_docs'])} new docs, "
          f"{len(out['restatements'])} restatements, {len(out.get('fetch_errors', []))} fetch errors")


if __name__ == "__main__":
    raise SystemExit(main())
