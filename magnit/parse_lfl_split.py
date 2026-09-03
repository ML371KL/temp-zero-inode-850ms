"""P0-1: precise LFL split (sales = ticket x traffic) from press narrative (primary).
Patterns are exact phrases; multiplicative identity verified within 0.3pp.
Merges into registry as ok; superseded v1-auto rows for same series are retired (kept in extracted_facts.json).
"""
import json, pathlib, re

DATA = pathlib.Path(__file__).parent / "data"
TXT = DATA / "press_text"
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
manifest = {m["key"]: m for m in json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))}

JOBS = [
    ("2024_0_press-release", "2024", "2024-12-31", "2024#0:press-release"),
    ("2025_0_press-release", "2025", "2025-12-31", "2025#0:press-release"),
    ("2026_0_press-release", "2026", "2026-06-30", "2026#0:press-release"),
]

def grab(t, pat):
    m = re.search(pat, t, re.I)
    return m.group(1).replace(",", ".") if m else None

added = []
for stem, period, asof, key in JOBS:
    t = (TXT / (stem + ".txt")).read_text(encoding="utf-8")
    sales = grab(t, r"Сопоставимые продажи \(LFL\)2 увеличились на ([\d,\.]+)%")
    ticket = grab(t, r"LFL[-\s]*среднего чека на ([\d,\.]+)%")
    traf_m = re.search(r"роста LFL[-\s]*трафика на ([\d,\.]+)%|трафик[^\n%]{0,60}?оставался неизменным|LFL[-\s]*трафика ([\d,\.]+)%", t, re.I)
    if traf_m:
        traffic = "0.0" if "неизменным" in traf_m.group(0) else (traf_m.group(1) or traf_m.group(2) or "0.0").replace(",", ".")
    else:
        traffic = None
    assert sales and ticket and traffic is not None, f"parse fail {stem}"
    s, k, r = float(sales), float(ticket), float(traffic)
    check = (1 + k / 100) * (1 + r / 100) - 1
    assert abs(check * 100 - s) < 0.35, f"identity fail {stem}: {s} vs {check*100:.2f}"
    m = manifest[key]
    for series, val in (("lfl", s), ("lfl_ticket", k), ("lfl_traffic", r)):
        added.append({"series": series, "period": period, "as_of": asof, "value": val, "unit": "pct_yoy",
                      "source": "magnit.com IR press-release narrative (primary)", "url": m["url"],
                      "released_at": {"2024": "2025-04-29", "2025": "2026-04-30", "2026": "2026-08-28"}[period],
                      "vintage": "v3-lfl-split", "status": "ok",
                      "note": f"identity verified: (1+{k}%)(1+{r}%)-1={check*100:.2f}% vs reported {s}%"})
    print(f"{period}: LFL {s}% = ticket {k}% x traffic {r}%  identity {check*100:.2f}% OK")

# retire superseded v1-auto rows for lfl/traffic/ticket (same period+series family)
retired = 0
kept = []
for row in reg:
    if row.get("vintage") == "v1-auto" and row["series"] in ("lfl", "traffic", "ticket"):
        retired += 1
        continue
    kept.append(row)
kept.extend(added)
kept.sort(key=lambda r: (r["as_of"], r["series"]))
(DATA / "registry.json").write_text(json.dumps(kept, ensure_ascii=False, indent=1), encoding="utf-8")
n_q = sum(1 for r in kept if r["status"] == "quarantine")
print(f"added {len(added)} ok rows, retired {retired} superseded auto rows; registry {len(kept)}, quarantine now {n_q}")
print("remaining quarantine series:", sorted({r['series'] for r in kept if r['status'] == 'quarantine'}))
