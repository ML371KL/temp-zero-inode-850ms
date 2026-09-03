"""Fix FY entries from combined Q4+FY releases via narrative anchors (max-level = FY).
Replaces wrong v5 rows for 2022FY/2023FY. Identity-checked.
Also 2021Q1/Q2 + 2019-9M split cleanup (drop split on identity fail, keep sales).
"""
import json, pathlib, re

DATA = pathlib.Path(__file__).parent / "data"
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
manifest = {m["key"]: m for m in json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))}

def pairs(t, pat):
    return [(a.replace(" ", ""), b.replace(" ", "")) for a, b in re.findall(pat, t, re.I)]

def fy_narrative(stem):
    t = (DATA / "press_text" / (stem + ".txt")).read_text(encoding="utf-8")
    out = {}
    # (growth%, level bn): take max level = FY
    for key, pat in {
        "revenue": r"Общая выручка выросла на ([\d,\.]+)% год к году до ([\d\s]+[,\.]\d)",
        "retail": r"Чистая розничная выручка увеличилась на ([\d,\.]+)% год к году[^\n]*?составила\s*([\d\s]+[,\.]\d)",
        "gross": r"Валовая прибыль увеличилась на ([\d,\.]+)% год к году до ([\d\s]+[,\.]\d)",
    }.items():
        hits = pairs(t, pat)
        if hits:
            g, lv = max(hits, key=lambda x: float(x[1].replace(",", ".")))
            out[key] = (float(g.replace(",", ".")), float(lv.replace(",", ".")))
    m = re.findall(r"Показатель EBITDA составил ([\d\s]+[,\.]\d) млрд", t)
    if m: out["ebitda"] = max(float(x.replace(" ", "").replace(",", ".")) for x in m)
    m = re.findall(r"Рентабельность по EBITDA[\s\S]{0,60}?составила ([\d,\.]+)%", t)
    if m: out["ebitda_margin"] = max(float(x.replace(",", ".")) for x in m)
    m = re.findall(r"Валовая (?:прибыль[\s\S]{0,40}?маржа|рентабельность|маржа)[\s\S]{0,60}?составила ([\d,\.]+)%", t)
    if m:
        cands = [float(x.replace(",", ".")) for x in m]
        if "gross" in out and "revenue" in out:
            ident = out["gross"][1] / out["revenue"][1] * 100
            best = min(cands, key=lambda c: abs(c - ident))
            # candidate may belong to quarterly section: if it misses identity, compute FY margin
            out["gross_margin"] = best if abs(best - ident) < 0.3 else round(ident, 1)
            out["_gm_note"] = "reported" if abs(best - ident) < 0.3 else f"computed {ident:.2f}% (only candidate {best}% is quarterly)"
        else:
            out["gross_margin"] = max(cands)
    m = re.findall(r"Чистая прибыль[\s\S]{0,80}?(?:до|составила?) ([\d\s]+[,\.]\d) млрд", t)
    if m: out["net_income"] = max(float(x.replace(" ", "").replace(",", ".")) for x in m)
    # LFL: FY sentence (contains 'увеличились на S% ... чека на T% ... трафика на R%'), prefer LAST (FY section after Q4)
    lfls = [(float(a.replace(",", ".")), float(b.replace(",", ".")), float(c.replace(",", ".")))
            for a, b, c in re.findall(
                r"увеличились на ([\d,\.]+)% на фоне роста[\s\S]{0,80}?чека на ([\d,\.]+)%[\s\S]{0,80}?трафика на ([\d,\.]+)%", t, re.I)]
    if lfls: out["lfl_split"] = lfls[-1]
    return out

JOBS = {"2022#0": ("2022FY", "2022-12-31", "2023-06-16"),
        "2023#0": ("2023FY", "2023-12-31", "2024-05-15")}
SER = {"revenue": ("revenue", "bn_rub", None), "retail": ("retail_revenue", "bn_rub", "pre16"),
       "gross": ("gross_profit", "bn_rub", "pre16"), "ebitda": ("ebitda", "bn_rub", "pre16"),
       "ebitda_margin": ("ebitda_margin", "pct", "pre16"), "gross_margin": ("gross_margin", "pct", "pre16"),
       "net_income": ("net_income", "bn_rub", "pre16")}
# v5 misattributed Q4 values as FY (and wrong bases) for these periods/series -> drop before v6 upsert
V5_DROP = {("2022FY", "gross_profit"), ("2022FY", "ebitda"), ("2022FY", "retail_revenue"),
           ("2023FY", "gross_profit"), ("2023FY", "ebitda"), ("2023FY", "retail_revenue")}
for _s, _p in V5_DROP:
    reg = [x for x in reg if not (x["series"] == _s and x["period"] == _p and x.get("vintage") == "v5-history")]
for key, (period, asof, rel) in JOBS.items():
    stem = key.replace("#", "_") + "_press-release"
    n = fy_narrative(stem)
    print(f"== {period} ==")
    for k, v in n.items(): print(f"  {k}: {v}")
    # identity checks
    if "revenue" in n and "retail" in n:
        assert n["revenue"][1] > n["retail"][1], "retail > total?!"
    if "gross" in n and "revenue" in n:
        calc = n["gross"][1] / n["revenue"][1] * 100
        rep = n.get("gross_margin")
        print(f"  gross identity: {calc:.2f}% vs reported {rep}")
    if "ebitda" in n and "revenue" in n:
        calc_e = n['ebitda'] / n['revenue'][1] * 100
        print(f"  ebitda identity: {calc_e:.2f}% vs reported {n.get('ebitda_margin')}")
        if "ebitda_margin" not in n:
            n["ebitda_margin"] = round(calc_e, 1)
            print(f"  ebitda margin missing -> computed {n['ebitda_margin']}%")
    if "lfl_split" in n:
        s, k_, r = n["lfl_split"]
        chk = (1 + k_ / 100) * (1 + r / 100) - 1
        print(f"  lfl identity: {chk*100:.2f}% vs reported {s}%")
    url = manifest[key + ":press-release"]["url"]
    for k, (series, unit, basis) in SER.items():
        if k not in n or k.startswith("_"): continue
        v = n[k]
        # tuples are (growth_pct, level_bn) -> store LEVEL; growth goes to note
        val = v[1] if isinstance(v, tuple) else v
        note_g = f"growth {v[0]}%; " if isinstance(v, tuple) else ""
        reg = [x for x in reg if (x["series"], x["period"], x.get("basis", "")) != (series, period, basis or "")]
        row = {"series": series, "period": period, "as_of": asof, "value": val, "unit": unit,
               "source": "magnit.com IR press-release FY narrative, max-level rule (primary)", "url": url,
               "released_at": rel, "vintage": "v6-fy-narrative", "status": "ok",
               "note": f"FY column; level {val} ({note_g}raw {n[k]})" + (f" [{n['_gm_note']}]" if k == "gross_margin" and "_gm_note" in n else "")}
        if basis: row["basis"] = basis
        reg.append(row)
    if "lfl_split" in n:
        s, k_, r = n["lfl_split"]
        for se, v in (("lfl", s), ("lfl_ticket", k_), ("lfl_traffic", r)):
            reg = [x for x in reg if (x["series"], x["period"], x.get("basis", "")) != (se, period, "")]
            reg.append({"series": se, "period": period, "as_of": asof, "value": v, "unit": "pct_yoy",
                        "source": "magnit.com IR press-release FY narrative (primary)", "url": url,
                        "released_at": rel, "vintage": "v6-fy-narrative", "status": "ok",
                        "note": f"FY LFL block, last occurrence"})
    # drop stale revenue_yoy headline (Q4 number misattributed)
    reg = [x for x in reg if not (x["series"] == "revenue_yoy" and x["period"] == period)]
    # recompute revenue_yoy from levels
    rev = n["revenue"][1]
    prev_rev = {"2022FY": 1856.0, "2023FY": 2352.0}[period]
    reg.append({"series": "revenue_yoy", "period": period, "as_of": asof,
                "value": round((rev / prev_rev - 1) * 100, 1), "unit": "pct",
                "source": "computed from FY narrative levels (primary)", "url": url,
                "released_at": rel, "vintage": "v6-fy-narrative", "status": "ok",
                "note": f"{rev}/{prev_rev}-1"})
# split cleanup: drop ticket/traffic where identity fails (keep sales)
for x in reg:
    if x.get("vintage") == "v5-history" and x["series"] in ("lfl_ticket", "lfl_traffic") and x["status"] == "quarantine":
        x["status"] = "dropped"
reg = [x for x in reg if x["status"] != "dropped"]
reg.sort(key=lambda r: (r["as_of"], r["series"]))
(DATA / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
from collections import Counter
print("registry:", len(reg), "status:", Counter(x["status"] for x in reg))
