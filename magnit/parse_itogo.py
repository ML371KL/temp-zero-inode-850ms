"""Definitive LFL split from 'Итого' table rows: [ticket, traffic, sales], paired (quarter, cumulative).
Takes LAST triplet for the entry period; FIRST triplet creates/updates the standalone quarter period.
Handles ASCII '-' and U+2212 minus. Identity-verified.
Upserts v7-itogo rows (replaces v5/v6 splits where better).
"""
import json, pathlib, re

DATA = pathlib.Path(__file__).parent / "data"
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
manifest = {m["key"]: m for m in json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))}
NUM = r"[-−]?[\d,\.]+"
PERIOD_OF_KEY = {
    "2022#0": ("2022FY", "2022-12-31", "2023-06-16", "2022Q4", "2022-12-31"),
    "2022#1": ("2022H1", "2022-06-30", "2022-08-19", None, None),
    "2022#2": ("2022H1", "2022-06-30", "2022-07-28", "2022Q2", "2022-06-30"),  # trading: H1 ex-Dixy cumulative
    "2022#3": ("2022Q1", "2022-03-31", "2022-04-29", None, None),
    "2023#0": ("2023FY", "2023-12-31", "2024-05-15", "2023Q4", "2023-12-31"),
    "2023#1": ("2023-9M", "2023-09-30", "2023-11-14", "2023Q3", "2023-09-30"),
    "2023#2": ("2023H1", "2023-06-30", "2023-08-29", "2023Q2", "2023-06-30"),
    "2023#3": ("2023Q1", "2023-03-31", "2023-06-16", None, None),
    "2024#0": ("2024FY", "2024-12-31", "2025-04-29", None, None),
    "2024#1": ("2024H1", "2024-06-30", "2024-08-30", None, None),
    "2025#0": ("2025FY", "2025-12-31", "2026-04-30", None, None),
    "2025#1": ("2025H1", "2025-06-30", "2025-08-29", None, None),
    "2026#0": ("2026H1", "2026-06-30", "2026-08-28", None, None),
    "arc2019#1": ("2019FY", "2019-12-31", "2020-02-06", "2019Q4", "2019-12-31"),
    "arc2019#0": ("2019FY", "2019-12-31", "2020-03-16", None, None),
    "arc2019#3": ("2019-9M", "2019-09-30", "2019-10-29", "2019Q3", "2019-09-30"),
    "arc2019#4": ("2019H1", "2019-06-30", "2019-08-20", None, None),
    "arc2019#5": ("2019H1", "2019-06-30", "2019-07-25", "2019Q2", "2019-06-30"),
    "arc2019#6": ("2019Q1", "2019-03-31", "2019-04-30", None, None),
    "arc2020#6": ("2020Q1", "2020-03-31", "2020-04-29", None, None),
    "arc2021#0": ("2021FY", "2021-12-31", "2022-03-04", None, None),
    "arc2021#1": ("2021FY", "2021-12-31", "2022-02-04", "2021Q4", "2021-12-31"),
    "arc2021#2": ("2021-9M", "2021-09-30", "2021-10-28", "2021Q3", "2021-09-30"),
    "arc2021#3": ("2021H1", "2021-06-30", "2021-08-19", None, None),
    "arc2021#4": ("2021H1", "2021-06-30", "2021-07-29", "2021Q2", "2021-06-30"),
    "arc2021#5": ("2021Q1", "2021-03-31", "2021-04-29", None, None),
}

def f(x): return float(x.replace("−", "-").replace(",", "."))

def itogo_triplets(t):
    """All 'Итого ...' LFL triplets (ticket, traffic, sales) in order, excluding SG&A rows.
    Labels may wrap across lines; combined releases carry quarter + cumulative (6 pcts)."""
    out = []
    pat = (r"Итого[\s\S]{0,150}?(" + NUM + r")%\s+(" + NUM + r")%\s+(" + NUM + r")%"
           r"(?:\s+(" + NUM + r")%\s+(" + NUM + r")%\s+(" + NUM + r")%)?")
    for m in re.finditer(pat, t):
        seg = t[max(0, m.start() - 60):m.start()]
        if re.search(r"расходы|SG&A|администр", seg, re.I): continue
        ctx = t[max(0, m.start() - 400):m.end() + 100]
        if not re.search(r"LFL|Магнит|формат|структура|чек|трафик", ctx, re.I): continue
        out.append((f(m.group(1)), f(m.group(2)), f(m.group(3))))
        if m.group(4) is not None:
            out.append((f(m.group(4)), f(m.group(5)), f(m.group(6))))
    return out

n_up = n_qdrop = 0
for key, (period, asof, rel, qperiod, qasof) in PERIOD_OF_KEY.items():
    mk = key + ":press-release"
    if mk not in manifest: continue
    # find press text file
    cands = list((DATA / "press_text").glob(key.replace("#", "_") + "*press-release.txt"))
    if not cands: continue
    t = cands[0].read_text(encoding="utf-8")
    trips = itogo_triplets(t)
    if not trips:
        # narrative fallback: 'выросли/увеличились на S% ... чека на T% ... [роста|снижения|сокращения] трафика на R%'
        m = re.search(r"[Вв]ыросли на ([\d,\.]+)% на фоне роста[\s\S]{0,120}?чека на ([\d,\.]+)%([\s\S]{0,150}?)", t)
        if not m:
            m = re.search(r"увеличились на ([\d,\.]+)% на фоне роста[\s\S]{0,120}?чека на ([\d,\.]+)%([\s\S]{0,150}?)", t)
        if m:
            s, k = f(m.group(1)), f(m.group(2))
            tail = m.group(3)
            tr = re.search(r"трафика на ([\d,\.]+)%", tail)
            if tr:
                r_ = f(tr.group(1))
                if re.search(r"снижения|сокращения|падения", tail[:tr.start()], re.I): r_ = -r_
                chk = (1 + k / 100) * (1 + r_ / 100) - 1
                if abs(chk * 100 - s) < 0.4:
                    trips = [(k, r_, s)]
                    print(f"{period}: narrative fallback {k}/{r_}/{s} ok")
        if not trips:
            print(f"{period}: no Итого LFL row"); continue
    url = manifest[mk]["url"]
    jobs = []
    if len(trips) >= 2 and qperiod:
        jobs.append((qperiod, qasof, trips[0], "quarterly column"))
        jobs.append((period, asof, trips[-1], "cumulative column"))
    else:
        jobs.append((period, asof, trips[-1] if len(trips) > 1 else trips[0], "single"))
    for p, a, (tk, tr, sa), col in jobs:
        chk = (1 + tk / 100) * (1 + tr / 100) - 1
        st = "ok" if abs(chk * 100 - sa) < 0.35 else "quarantine"
        for se, v in (("lfl", sa), ("lfl_ticket", tk), ("lfl_traffic", tr)):
            reg = [x for x in reg if (x["series"], x["period"], x.get("basis", "")) != (se, p, "")]
            reg.append({"series": se, "period": p, "as_of": a, "value": v, "unit": "pct_yoy",
                        "source": "magnit.com IR press-release LFL table, Итого row (primary)", "url": url,
                        "released_at": rel, "vintage": "v7-itogo", "status": st,
                        "note": f"{col}; identity {(1+tk/100)*(1+tr/100)-1:.2%} vs {sa}%"})
            n_up += 1
        print(f"{p}: ticket {tk}% traffic {tr}% sales {sa}% [{st}] ({col})")
reg.sort(key=lambda r: (r["as_of"], r["series"]))
(DATA / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
from collections import Counter
print(f"upserted {n_up}; registry {len(reg)}", Counter(x["status"] for x in reg))
