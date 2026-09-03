"""P0-1b: add pre16 margins from pnl.json table pairs, retire remaining margin/yoy quarantine rows."""
import json, pathlib

DATA = pathlib.Path(__file__).parent / "data"
pnl = json.loads((DATA / "pnl.json").read_text(encoding="utf-8"))
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
manifest = {m["key"]: m for m in json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))}
MAP = {"2024_0_press-release": ("2024", "2024-12-31", "2024#0:press-release", "2025-04-29"),
       "2025_0_press-release": ("2025", "2025-12-31", "2025#0:press-release", "2026-04-30"),
       "2026_0_press-release": ("2026", "2026-06-30", "2026#0:press-release", "2026-08-28")}
added = 0
for stem, (period, asof, key, rel) in MAP.items():
    t = pnl[stem]["table"]
    for src, dst in (("gross_margin", "gross_margin"), ("ebitda_margin", "ebitda_margin")):
        if src not in t: continue
        cur = float(t[src][0].replace("%", "").replace(",", "."))
        reg.append({"series": dst, "basis": "pre16", "period": period, "as_of": asof, "value": cur,
                    "unit": "pct", "source": "magnit.com IR press-release P&L table (primary)",
                    "url": manifest[key]["url"], "released_at": rel, "vintage": "v2-pnl-table",
                    "status": "ok", "note": f"pre-IFRS16 headline; prev {t[src][1]}"})
        added += 1
kept = [r for r in reg if not (r.get("vintage") == "v1-auto" and r["series"] in ("ebitda_margin", "gross_margin", "revenue_yoy", "revenue"))]
kept.sort(key=lambda r: (r["as_of"], r["series"]))
(DATA / "registry.json").write_text(json.dumps(kept, ensure_ascii=False, indent=1), encoding="utf-8")
n_q = sum(1 for r in kept if r["status"] == "quarantine")
print(f"added {added} margin rows; registry {len(kept)}, quarantine now {n_q}")
print("remaining quarantine:", sorted({(r['series'], r['period']) for r in kept if r['status'] == 'quarantine'}))
