"""Parse full IR press-release history (2019-2026) with upsert into registry.
Explicit period map from catalog names. Revenue yoy + LFL split always;
full P&L table for H1/FY entries. Identity checks; failures -> quarantine.
Upsert key: (series, period, basis).
"""
import json, pathlib, re, datetime
from pypdf import PdfReader

DATA = pathlib.Path(__file__).parent / "data"
PDFS = DATA / "pdfs"
TXT = DATA / "press_text"
MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
RU_M = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
        "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}

PERIODS = {
    # key: (period, as_of)
    "2022#0": ("2022FY", "2022-12-31"), "2022#1": ("2022H1", "2022-06-30"),
    "2022#2": ("2022Q2", "2022-06-30"), "2022#3": ("2022Q1", "2022-03-31"),
    "2023#0": ("2023FY", "2023-12-31"), "2023#1": ("2023-9M", "2023-09-30"),
    "2023#2": ("2023H1", "2023-06-30"), "2023#3": ("2023Q1", "2023-03-31"),
    "2024#0": ("2024FY", "2024-12-31"), "2024#1": ("2024H1", "2024-06-30"),
    "2025#0": ("2025FY", "2025-12-31"), "2025#1": ("2025H1", "2025-06-30"),
    "2026#0": ("2026H1", "2026-06-30"),
    "arc2019#0": ("2019FY", "2019-12-31"), "arc2019#1": ("2019Q4", "2019-12-31"),
    "arc2019#3": ("2019-9M", "2019-09-30"), "arc2019#4": ("2019H1", "2019-06-30"),
    "arc2019#5": ("2019Q2", "2019-06-30"), "arc2019#6": ("2019Q1", "2019-03-31"),
    "arc2020#0": ("2020FY", "2020-12-31"), "arc2020#1": ("2020Q4", "2020-12-31"),
    "arc2020#3": ("2020-9M", "2020-09-30"), "arc2020#4": ("2020H1", "2020-06-30"),
    "arc2020#5": ("2020Q2", "2020-06-30"), "arc2020#6": ("2020Q1", "2020-03-31"),
    "arc2021#0": ("2021FY", "2021-12-31"), "arc2021#1": ("2021Q4", "2021-12-31"),
    "arc2021#2": ("2021-9M", "2021-09-30"), "arc2021#3": ("2021H1", "2021-06-30"),
    "arc2021#4": ("2021Q2", "2021-06-30"), "arc2021#5": ("2021Q1", "2021-03-31"),
}
FULL_PNL = ("H1", "FY")  # entry types with full P&L table

def released_at(fname, text):
    m = re.search(r"(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{4})", fname)
    if m: return datetime.date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1))).isoformat()
    for m2 in re.finditer(r"(\d{1,2})\s+([а-я]+)\s+(\d{4})\s*г", text[:1500]):
        if m2.group(2) in RU_M:
            return datetime.date(int(m2.group(3)), RU_M[m2.group(2)], int(m2.group(1))).isoformat()
    return ""

def grab1(t, pat):
    m = re.search(pat, t, re.I | re.S)
    return m.group(1).replace(",", ".").replace(" ", "") if m else None

def main():
    manifest = {m["key"]: m for m in json.loads((PDFS / "manifest.json").read_text(encoding="utf-8"))}
    reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
    n_new, n_q = 0, 0
    for key, (period, asof) in PERIODS.items():
        if period in ("2024FY", "2025FY", "2026H1") and key in ("2024#0", "2025#0", "2026#0"):
            continue  # already parsed precisely
        m = manifest.get(key + ":press-release")
        if not m:
            print(f"SKIP {key}: no press-release in manifest"); continue
        f = PDFS / m["file"]
        if not f.exists():
            print(f"SKIP {key}: file missing"); continue
        rd = PdfReader(str(f))
        t = "\n".join((p.extract_text() or "") for p in rd.pages)
        (TXT / (key.replace("#", "_") + "_press-release.txt")).write_text(t, encoding="utf-8")
        rel = released_at(m["file"], t) or m["fetched_at_utc"][:10]
        rows = []
        if len(t) < 2000:
            print(f"{period}: SCANNED PDF ({len(t)} chars) — primary text unavailable, needs OCR/secondary")
            continue
        # revenue yoy: prefer ОБЩАЯ (total); fallback retail with note. Several phrasings.
        rev, rev_basis = None, ""
        for pat, basis in ((r"ОБЪЯВЛЯЕТ О РОСТЕ ОБЩЕЙ\s*\n?ВЫРУЧКИ НА\s*([\d\s]+[,\.]\d)\s*%", "total"),
                           (r"[Оо]бщая выручка[^\n%]{0,60}?на ([\d\s]+[,\.]\d)\s*%", "total"),
                           (r"[Рр]ост[^\n%]{0,60}?выручк[^\n%]{0,40}?на ([\d\s]+[,\.]\d)\s*%", "unspecified"),
                           (r"выручк[^\n%]{0,80}?увеличилась на ([\d\s]+[,\.]\d)\s*%", "unspecified"),
                           (r"объявляет о росте выручки на ([\d\s]+[,\.]\d)\s*%", "unspecified")):
            rev = grab1(t, pat)
            if rev: rev_basis = basis; break
        # LFL block: anchor on sales sentence, take ticket/traffic within +250 chars
        lfl_m = re.search(r"[Сс]опоставимые продажи \(LFL\)[^\n]{0,80}?на ([\d,\.]+)%", t)
        lfl = lfl_m.group(1).replace(",", ".") if lfl_m else grab1(t, r"LFL[^\n]{0,60}?на ([\d,\.]+)%")
        ticket, traffic, tstat = None, None, "ok"
        if lfl_m:
            win = t[lfl_m.start():lfl_m.start() + 300]
            tm = re.search(r"среднего чека на ([\d,\.]+)%", win, re.I)
            ticket = tm.group(1).replace(",", ".") if tm else None
            tr = re.search(r"трафика на ([\d,\.]+)%|трафик[^\n%]{0,60}?оставался неизменным", win, re.I)
            if tr:
                traffic = "0.0" if "неизменным" in tr.group(0) else (tr.group(1).replace(",", ".") if tr.lastindex else None)
            if ticket is not None and abs(float(ticket) - float(lfl)) > 12:
                tstat = "quarantine"  # format-level number leaked in; do not trust split
                ticket, traffic = None, None
        def add(series, val, unit, status, note):
            rows.append({"series": series, "period": period, "as_of": asof, "value": val, "unit": unit,
                         "source": "magnit.com IR press-release (primary)", "url": m["url"],
                         "released_at": rel, "vintage": "v5-history", "status": status, "note": note})
        ok = True
        rev_row = None
        if rev: rev_row = (float(rev), f"headline yoy ({rev_basis})")
        else: ok = False
        if lfl and ticket and traffic is not None and tstat == "ok":
            s, k, r = float(lfl), float(ticket), float(traffic)
            chk = (1 + k / 100) * (1 + r / 100) - 1
            st = "ok" if abs(chk * 100 - s) < 0.4 else "quarantine"
            for se, v in (("lfl", s), ("lfl_ticket", k), ("lfl_traffic", r)):
                add(se, v, "pct_yoy", st, f"identity {(1+k/100)*(1+r/100)-1:.2%}" if st == "ok" else "identity MISMATCH")
            if st == "quarantine": n_q += 1
        else:
            if lfl: add("lfl", float(lfl), "pct_yoy", "ok" if tstat == "ok" else "quarantine",
                        "sales only; split missing" if tstat == "ok" else "split failed validation")
            if tstat == "quarantine": n_q += 1
            ok = False
        # full P&L for H1/FY — slice the cumulative table region (combined releases lead with quarterly tables)
        tb = {}
        if period.endswith(("H1", "FY")):
            import sys
            sys.path.insert(0, str(DATA.parent))
            from parse_pnl_tables import parse_pnl as pp
            want_cumul = "12 месяцев" if period.endswith("FY") else "1 полугодие"
            alts = {"12 месяцев": ["12 месяцев", "12M", "12 месяцев 20", "2022 года", "2023 года", "2024 года"],
                    "1 полугодие": ["1 полугодие", "6 месяцев", "1П ", "полугодие"]}
            region = t
            for mk in alts[want_cumul]:
                ii = t.find(mk)
                if ii != -1:
                    region = t[ii:ii + 6000]
                    break
            p = pp(region if region is not t else t)
            tb = p["table"]
            # magnitude guard: FY revenue must exceed 1.2M millions; H1 must exceed 0.6M
            if "revenue_total" in tb and not isinstance(tb["revenue_total"][0], list):
                lvl = tb["revenue_total"][0]
                need = 1200000 if period.endswith("FY") else 600000
                if lvl < need:  # grabbed quarterly table -> drop P&L, keep headline only
                    print(f"{period}: P&L region looks quarterly (rev {lvl}) -> dropped, headline only")
                    tb = {}
            for src, dst in (("revenue_total", "revenue"), ("gross_profit", "gross_profit"),
                             ("ebitda", "ebitda"), ("ebit", "ebit")):
                if src not in tb: continue
                v = tb[src]
                if isinstance(v[0], list):
                    for basis, trip in (("pre16", v[0]), ("post16", v[1] if len(v) > 1 else v[0])):
                        add(dst, round(trip[0] / 1000, 1), "bn_rub", "ok", f"basis {basis}; yoy {trip[2]}")
                        rows[-1]["basis"] = basis
                else:
                    add(dst, round(v[0] / 1000, 1), "bn_rub", "ok", f"yoy {v[2]}")
            for src, dst in (("ebitda_margin", "ebitda_margin"),):
                if src in tb:
                    add(dst, float(tb[src][0].replace("%", "").replace(",", ".")), "pct", "ok", "pre16 headline")
                    rows[-1]["basis"] = "pre16"
            gm = re.search(r"Валовая маржа[^\n%]{0,60}?до ([\d,\.]+)%", t)
            if gm:
                add("gross_margin", float(gm.group(1).replace(",", ".")), "pct", "ok", "narrative pre16")
                rows[-1]["basis"] = "pre16"
            nd = re.findall(r"чистый долг, млрд руб\.\s+([\d\s]+[,\.]\d)\s+([\d\s]+[,\.]\d)", t, re.I)
            if nd:
                add("net_debt", float(nd[0][0].replace(" ", "").replace(",", ".")), "bn_rub", "ok", f"pre16; prev {nd[0][1]}")
                rows[-1]["basis"] = "pre16"
                if len(nd) > 1:
                    add("net_debt", float(nd[1][0].replace(" ", "").replace(",", ".")), "bn_rub", "ok", f"post16; prev {nd[1][1]}")
                    rows[-1]["basis"] = "post16"
        # reconcile headline yoy vs P&L levels (combined Q4+FY releases often lead with quarterly number)
        if "revenue_total" in tb and not isinstance(tb["revenue_total"][0], list):
            a, b = tb["revenue_total"][0], tb["revenue_total"][1]
            calc = round((a / b - 1) * 100, 1)
            if rev_row and abs(rev_row[0] - calc) > 1.5:
                add("revenue_yoy", calc, "pct", "ok",
                    f"computed from P&L levels; headline {rev_row[0]}% looks quarterly -> quarantined-headline")
                n_q += 1
                rev_row = None  # already added computed; skip headline below
            elif rev_row is None:
                add("revenue_yoy", calc, "pct", "ok", "computed from P&L levels")
                rev_row = (calc, "computed")
        if rev_row and not any(r["series"] == "revenue_yoy" for r in rows):
            add("revenue_yoy", rev_row[0], "pct", "ok", rev_row[1])
        elif not rev_row:
            ok = False
        for r in rows:
            uk = (r["series"], r["period"], r.get("basis", ""))
            reg = [x for x in reg if (x["series"], x["period"], x.get("basis", "")) != uk]
            reg.append(r)
            n_new += 1
        print(f"{period}: rev_yoy={rev} lfl={lfl}/{ticket}/{traffic} rows={len(rows)} rel={rel} {'PARTIAL' if not ok else ''}")
    reg.sort(key=lambda r: (r["as_of"], r["series"]))
    (DATA / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"upserted {n_new} rows; registry {len(reg)}")

if __name__ == "__main__":
    main()
