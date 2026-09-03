"""P0-2: organic (M&A-adjusted) revenue base. LFL already organic by 12-month rule;
total revenue adjusted via IFRS note-7 contributions (primary source).
Samberi/DV Nevada: 11 Jan 2024, 2024 contrib 100.5bn. Azbuka: 20 May 2025,
2025 contrib 66.0bn (pro-forma FY +40.4bn), H1 2025 contrib 11.6bn, H1 2026 ~54bn EST.
Saves organic series into registry (v4-organic) + magnit/data/organic.json
"""
import json, pathlib

DATA = pathlib.Path(__file__).parent / "data"
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))

ORG = [
    # period, as_of, reported_rev, ma_rev, ma_note, released_at, url_key
    ("2024", "2024-12-31", 3043.4, 100.5, "DV Nevada/Samberi 11Jan-31Dec2024 (IFRS note 7: 100501597k)", "2025-04-29", "2024#0:press-release"),
    ("2025", "2025-12-31", 3509.2, 66.0, "Azbuka 20May-31Dec2025 (IFRS note 7: 65962025k; pro-forma FY +40.4bn)", "2026-04-30", "2025#0:press-release"),
    ("2026H1", "2026-06-30", 1887.2, 54.0, "Azbuka H1 2026 EST ~54bn (7.3mo 66.0bn in H2 2025 -> ~9.0bn/mo); band +-3bn", "2026-08-28", "2026#0:press-release"),
]
BASE = {  # prior-year base in SAME scope (Samberi in both FY24/FY25 nearly fully; Azbuka excluded both sides)
    "2024": ("2023 reported (no Samberi)", 2544.7),
    "2025": ("2024 reported incl Samberi 11Jan-31Dec (pro-forma full-year diff only +2.2bn, immaterial)", 3043.4),
    "2026H1": ("H1 2025 ex-Azbuka-partial (1673.2-11.6)", 1661.6),
}
manifest = {m["key"]: m for m in json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))}
out = []
for period, asof, rep, ma, note, rel, key in ORG:
    bnote, base = BASE[period]
    org_rev = round(rep - ma, 1)
    g = round((org_rev / base - 1) * 100, 1)
    rep_g = round((rep / (base + (ma if period != '2025' else 0)) - 1) * 100, 1) if False else None
    row = {"series": "revenue_organic", "period": period, "as_of": asof, "value": org_rev, "unit": "bn_rub",
           "source": "press total minus IFRS note-7 M&A contribution (primary+primary)",
           "url": manifest[key]["url"], "released_at": rel, "vintage": "v4-organic", "status": "ok" if period != "2026H1" else "provisional",
           "note": note + f"; base {bnote}={base}"}
    out.append({**row, "organic_yoy_pct": g})
    reg.append({**row, "note": row["note"] + f"; organic yoy {g}%"})
    print(f"{period}: reported {rep} - M&A {ma} = organic {org_rev} vs base {base} -> organic yoy {g}%")
reg.sort(key=lambda r: (r["as_of"], r["series"]))
(DATA / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
(DATA / "organic.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("organic gaps vs X5 (24.2/18.8/10.6): FY24 -8.6pp, FY25 -5.7pp, H1 ~-0.2pp -> CONVERGENCE")
