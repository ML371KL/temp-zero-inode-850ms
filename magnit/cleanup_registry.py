"""Registry cleanup: FY levels, H1/Q splits, period normalization, computed yoy rows."""
import json, pathlib

DATA = pathlib.Path(__file__).parent / "data"
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
manifest = {m["key"]: m for m in json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))}
U25 = manifest["2025#1:press-release"]["url"]

def upsert(row):
    global reg
    uk = (row["series"], row["period"], row.get("basis", ""))
    reg = [x for x in reg if (x["series"], x["period"], x.get("basis", "")) != uk]
    reg.append(row)

def R(series, period, asof, val, unit, basis, note, rel, url, vintage, status="ok"):
    r = {"series": series, "period": period, "as_of": asof, "value": val, "unit": unit,
         "source": "magnit.com IR press-release (primary)", "url": url, "released_at": rel,
         "vintage": vintage, "status": status, "note": note}
    if basis: r["basis"] = basis
    return r

# 1. FY revenue levels (were growth% due to v6 tuple bug)
upsert(R("revenue", "2022FY", "2022-12-31", 2352.0, "bn_rub", None, "+26.7% to 2352.0bn (narrative)", "2023-06-16",
         manifest["2022#0:press-release"]["url"], "v6-fy-narrative"))
upsert(R("revenue", "2023FY", "2023-12-31", 2544.7, "bn_rub", None, "+8.2% to 2544.7bn (narrative)", "2024-05-15",
         manifest["2023#0:press-release"]["url"], "v6-fy-narrative"))
# 2. 2023H1 level + 2023Q2 split
U232 = manifest["2023#2:press-release"]["url"]
upsert(R("revenue", "2023H1", "2023-06-30", 1229.5, "bn_rub", None, "+8.2% H1 level (was Q2 632.7 misattributed)", "2023-08-29", U232, "v7-itogo"))
upsert(R("revenue", "2023Q2", "2023-06-30", 632.7, "bn_rub", None, "+7.5% Q2 level", "2023-08-29", U232, "v7-itogo"))
upsert(R("revenue_yoy", "2023Q2", "2023-06-30", 7.5, "pct", None, "Q2 headline", "2023-08-29", U232, "v7-itogo"))
# 3. Q1 levels
upsert(R("revenue", "2023Q1", "2023-03-31", 596.8, "bn_rub", None, "+9.0% Q1 level", "2023-06-16",
         manifest["2023#3:press-release"]["url"], "v7-itogo"))
upsert(R("revenue", "2022Q1", "2022-03-31", 547.7, "bn_rub", None, "+37.7% Q1 level (Dixy in base? no: Q1'21 ex-Dixy)", "2022-04-29",
         manifest["2022#3:press-release"]["url"], "v7-itogo"))
# 4. normalize legacy periods + drop superseded v1 rows
for x in reg:
    if x["period"] == "2024": x["period"] = "2024FY"; x["as_of"] = "2024-12-31"
    if x["period"] == "2025": x["period"] = "2025FY"; x["as_of"] = "2025-12-31"
    if x["period"] == "2026": x["period"] = "2026H1"; x["as_of"] = "2026-06-30"
    if x["period"] == "2024#0": x["period"] = "2024FY"; x["as_of"] = "2024-12-31"
    if x["period"] == "2025#0": x["period"] = "2025FY"; x["as_of"] = "2025-12-31"
    if x["period"] == "2026#0": x["period"] = "2026H1"; x["as_of"] = "2026-06-30"
reg = [x for x in reg if not (x.get("vintage") == "v1-press-text" and x["period"] in ("2024FY", "2025FY", "2026H1"))]
import datetime as _dt
TODAY = _dt.date.today().isoformat()
# 5. computed yoy from levels
lv = {}
for x in reg:
    if x["series"] == "revenue" and x["unit"] == "bn_rub" and x.get("basis") not in ("pre16", "post16"):
        lv[x["period"]] = x["value"]
pairs = [("2020FY", "2019FY"), ("2021FY", "2020FY"), ("2022FY", "2021FY"), ("2023FY", "2022FY"),
         ("2024FY", "2023FY"), ("2025FY", "2024FY")]
for cur, prev in pairs:
    if cur in lv and prev in lv and not any(x["series"] == "revenue_yoy" and x["period"] == cur for x in reg):
        upsert(R("revenue_yoy", cur, next(x["as_of"] for x in reg if x["series"] == "revenue" and x["period"] == cur),
                 round((lv[cur] / lv[prev] - 1) * 100, 1), "pct", None, f"computed {lv[cur]}/{lv[prev]}-1",
                 TODAY, "", "v7-computed"))
h1 = [("2024H1", 1460.1, 1229.5), ("2025H1", 1673.2, 1460.1), ("2026H1", 1887.2, 1673.2)]
for p, c, b in h1:
    if not any(x["series"] == "revenue_yoy" and x["period"] == p for x in reg):
        asof = next((x["as_of"] for x in reg if x["series"] == "revenue" and x["period"] == p), "")
        upsert(R("revenue_yoy", p, asof, round((c / b - 1) * 100, 1), "pct", None, f"computed {c}/{b}-1", TODAY, "", "v7-computed"))
reg.sort(key=lambda r: (r["as_of"], r["series"]))
(DATA / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
from collections import Counter
print("registry:", len(reg), Counter(x["status"] for x in reg))
print("yoy origins:", sorted({x["period"] for x in reg if x["series"] == "revenue_yoy"}))
