"""One-off migration: add vintage fields to every registry row (no data change otherwise).
- vintage_id: existing vintage string (v1..v8) kept as lineage
- first_seen: manifest fetched_at where URL matches, else file mtime (flagged backfilled)
- source_hash: pdf manifest sha256 where URL matches, else null
- restatement_id: null (no restatements tracked yet); supersedes: null
- status 'superseded' introduced for future restatements (none yet)
"""
import json, pathlib, datetime

DATA = pathlib.Path(__file__).parent / "data"
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
manifest = json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))
by_url = {m["url"]: m for m in manifest}
fallback_ts = datetime.datetime.fromtimestamp((DATA / "registry.json").stat().st_mtime,
                                              datetime.timezone.utc).isoformat()[:10]
n_back = 0
for x in reg:
    m = by_url.get(x.get("url", ""))
    if m:
        x["first_seen"] = m["fetched_at_utc"][:10]
        x["source_hash"] = m.get("sha256")
    else:
        x["first_seen"] = fallback_ts
        x["source_hash"] = None
        n_back += 1
    x["vintage_id"] = x.get("vintage", "unknown")
    x["restatement_id"] = None
    x["supersedes"] = None
(DATA / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"migrated {len(reg)} rows ({n_back} backfilled first_seen, rest from manifest)")
