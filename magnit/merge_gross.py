"""P0-1c: gross margins from narrative 'до X%' + identity check gross_profit/revenue."""
import json, pathlib, re

DATA = pathlib.Path(__file__).parent / "data"
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
manifest = {m["key"]: m for m in json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))}
JOBS = [("2024_0_press-release", "2024", "2024-12-31", "2024#0:press-release", "2025-04-29", 684.4, 3043.4),
        ("2025_0_press-release", "2025", "2025-12-31", "2025#0:press-release", "2026-04-30", 784.1, 3509.2),
        ("2026_0_press-release", "2026", "2026-06-30", "2026#0:press-release", "2026-08-28", 437.0, 1887.2)]
for stem, period, asof, key, rel, gp, rev in JOBS:
    t = (DATA / "press_text" / (stem + ".txt")).read_text(encoding="utf-8")
    m = re.search(r"Валовая маржа[^\n%]{0,60}?до ([\d,\.]+)%", t)
    assert m, stem
    rep = float(m.group(1).replace(",", "."))
    calc = gp / rev * 100
    assert abs(rep - calc) < 0.15, (stem, rep, calc)
    reg.append({"series": "gross_margin", "basis": "pre16", "period": period, "as_of": asof, "value": rep,
                "unit": "pct", "source": "magnit.com IR press-release narrative (primary)",
                "url": manifest[key]["url"], "released_at": rel, "vintage": "v3-margins",
                "status": "ok", "note": f"identity: {gp}/{rev}={calc:.2f}% vs reported {rep}%"})
    print(f"{period}: gross margin {rep}% (calc {calc:.2f}%) OK")
reg.sort(key=lambda r: (r["as_of"], r["series"]))
(DATA / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
print("registry:", len(reg))
