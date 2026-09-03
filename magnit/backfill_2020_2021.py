"""Backfill 2021FY levels + 2020FY prior-year columns (primary: audited FY2021 release).
2020 press PDFs are scanned -> levels come from 2021 release prior-year columns (primary-derived, ok).
"""
import json, pathlib

DATA = pathlib.Path(__file__).parent / "data"
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
URL21 = "https://www.magnit.com/upload/iblock/ed8/Magnit_FY2021_4Mar2022_rus.pdf"  # placeholder, replaced below
manifest = {m["key"]: m for m in json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))}
URL21 = manifest["arc2021#0:press-release"]["url"]
REL21 = "2022-03-04"

def add(series, period, asof, val, unit, basis, note, rel, url, vintage="v6-fy-narrative"):
    row = {"series": series, "period": period, "as_of": asof, "value": val, "unit": unit,
           "source": "magnit.com IR audited FY2021 release incl prior-year columns (primary)",
           "url": url, "released_at": rel, "vintage": vintage, "status": "ok", "note": note}
    if basis: row["basis"] = basis
    return row

new = [
    add("revenue", "2021FY", "2021-12-31", 1856.1, "bn_rub", None, "+19.5% to 1856.1bn", REL21, URL21),
    add("net_income", "2021FY", "2021-12-31", 51.7, "bn_rub", "pre16", "+36.8%; post16 48.1/33.0", REL21, URL21),
    add("revenue", "2020FY", "2020-12-31", round(1856.1 / 1.195, 1), "bn_rub", None, "computed 1856.1/1.195 (primary-derived)", "2022-03-04", URL21, "v6-derived"),
    add("ebitda", "2020FY", "2020-12-31", 109.4, "bn_rub", "pre16", "prior-year column FY2021 table (21.7% yoy)", "2022-03-04", URL21, "v6-derived"),
    add("ebitda", "2020FY", "2020-12-31", 178.2, "bn_rub", "post16", "prior-year column (20.2% yoy)", "2022-03-04", URL21, "v6-derived"),
    add("gross_profit", "2020FY", "2020-12-31", round(439.2 / 1.201, 1), "bn_rub", "pre16", "computed 439.2/1.201 (20.1% yoy stated)", "2022-03-04", URL21, "v6-derived"),
    add("net_income", "2020FY", "2020-12-31", 37.8, "bn_rub", "pre16", "prior-year column; post16 33.0", "2022-03-04", URL21, "v6-derived"),
    add("net_debt", "2020FY", "2020-12-31", 136.1, "bn_rub", "pre16", "prior-year column; post16 498.9", "2022-03-04", URL21, "v6-derived"),
    add("stores", "2021FY", "2021-12-31", 26077, "count", None, "key-figures cross-check pending", REL21, URL21),
]
for r in new:
    uk = (r["series"], r["period"], r.get("basis", ""))
    reg = [x for x in reg if (x["series"], x["period"], x.get("basis", "")) != uk]
    reg.append(r)
reg.sort(key=lambda r: (r["as_of"], r["series"]))
(DATA / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
from collections import Counter
print("registry:", len(reg), Counter(x["status"] for x in reg))
print("origins with revenue_yoy:", sorted({x["period"] for x in reg if x["series"] == "revenue_yoy"}))
