"""Merge precise P&L facts from pnl.json into registry.json (ok status, both bases).
Units: millions->bn. released_at from manifest filename dates.
"""
import json, pathlib, re, datetime

DATA = pathlib.Path(__file__).parent / "data"
pnl = json.loads((DATA / "pnl.json").read_text(encoding="utf-8"))
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
manifest = {m["key"]: m for m in json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))}
MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

def rel(key):
    fn = manifest[key]["file"]
    mt = re.search(r"(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{4})", fn)
    return datetime.date(int(mt.group(3)), MONTHS[mt.group(2)], int(mt.group(1))).isoformat()

MAP = {"2024_0_press-release": ("2024", "2024-12-31", "2024#0:press-release"),
       "2025_0_press-release": ("2025", "2025-12-31", "2025#0:press-release"),
       "2026_0_press-release": ("2026", "2026-06-30", "2026#0:press-release")}

SERIES = [("revenue_total", "revenue", 1e-3, "bn_rub"),
          ("gross_profit", "gross_profit", 1e-3, "bn_rub"),
          ("ebitda", "ebitda", 1e-3, "bn_rub"),
          ("ebit", "ebit", 1e-3, "bn_rub")]

added = 0
for stem, (period, asof, key) in MAP.items():
    t = pnl[stem]["table"]
    url = manifest[key]["url"]
    rdate = rel(key)
    for src, dst, k, unit in SERIES:
        if src not in t: continue
        v = t[src]
        if isinstance(v[0], list):  # [pre_triplet, post_triplet]
            pre, post = v[0][0] * k, v[1][0] * k
            for basis, val in (("pre16", pre), ("post16", post)):
                reg.append({"series": dst, "basis": basis, "period": period, "as_of": asof,
                            "value": round(val, 1), "unit": unit, "source": "magnit.com IR press-release P&L table (primary)",
                            "url": url, "released_at": rdate, "vintage": "v2-pnl-table", "status": "ok",
                            "note": f"cur period; prev: pre={v[0][1]*k:.1f} post={v[1][1]*k:.1f}, yoy pre={v[0][2]}"})
                added += 1
        else:  # single triplet (revenue)
            reg.append({"series": dst, "basis": "n/a", "period": period, "as_of": asof,
                        "value": round(v[0] * k, 1), "unit": unit, "source": "magnit.com IR press-release P&L table (primary)",
                        "url": url, "released_at": rdate, "vintage": "v2-pnl-table", "status": "ok",
                        "note": f"yoy {v[2]}"})
            added += 1
    d = pnl[stem]["debt"]
    if d.get("net_debt_pairs"):
        (pre_cur, pre_prev), *rest = d["net_debt_pairs"]
        reg.append({"series": "net_debt", "basis": "pre16", "period": period, "as_of": asof,
                    "value": float(pre_cur.replace(",", ".")), "unit": "bn_rub",
                    "source": "magnit.com IR press-release debt table (primary)", "url": url,
                    "released_at": rdate, "vintage": "v2-pnl-table", "status": "ok", "note": f"prev {pre_prev}"})
        added += 1
        if rest:
            reg.append({"series": "net_debt", "basis": "post16", "period": period, "as_of": asof,
                        "value": float(rest[0][0].replace(",", ".")), "unit": "bn_rub",
                        "source": "magnit.com IR press-release debt table (primary)", "url": url,
                        "released_at": rdate, "vintage": "v2-pnl-table", "status": "ok", "note": f"prev {rest[0][1]}"})
            added += 1
    if pnl[stem]["capex"]:
        m = re.search(r"составили ([\d,\.]+)", pnl[stem]["capex"])
        if m:
            reg.append({"series": "capex_exMA", "basis": "n/a", "period": period, "as_of": asof,
                        "value": float(m.group(1).replace(",", ".")), "unit": "bn_rub",
                        "source": "magnit.com IR press-release (primary)", "url": url,
                        "released_at": rdate, "vintage": "v2-pnl-table", "status": "ok",
                        "note": pnl[stem]["capex"][:140]})
            added += 1
    if pnl[stem]["cost_of_debt"]:
        m = re.search(r"до ([\d,\.]+%)", pnl[stem]["cost_of_debt"])
        if m:
            reg.append({"series": "cost_of_debt", "basis": "n/a", "period": period, "as_of": asof,
                        "value": float(m.group(1).replace("%", "").replace(",", ".")), "unit": "pct",
                        "source": "magnit.com IR press-release (primary)", "url": url,
                        "released_at": rdate, "vintage": "v2-pnl-table", "status": "ok", "note": "weighted-average cost of debt"})
            added += 1

reg.sort(key=lambda r: (r["as_of"], r["series"], r.get("basis", "")))
(DATA / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"added {added} precise rows; registry total {len(reg)}")
