"""OPEX bridge (company level, primary sources only) + format revenue splits.
Levels where disclosed (personnel IFRS, rent cash CF, D&A, SG&A totals, other income),
component bps deltas from narrative otherwise (levels undisclosed -> direction only).
Format revenue: press P&L format tables (convenience/Dixy/drogerie/supermarkets);
remainder = Market/Samberi/Azbuka/other (flagged, not split).
Saves magnit/data/opex_bridge.json
"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_pnl_tables import split_groups
import json, pathlib, re

DATA = pathlib.Path(__file__).parent / "data"
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
pnl = json.loads((DATA / "pnl.json").read_text(encoding="utf-8"))
TXT = DATA / "press_text"

lv = {}
for x in reg:
    if x["status"] == "ok" and x["unit"] == "bn_rub" and x.get("basis", "n/a") in ("pre16", "n/a", None, ""):
        lv.setdefault((x["series"], x["period"]), x["value"])


def sga_pct(stem):
    t = (TXT / (stem + ".txt")).read_text(encoding="utf-8") if (TXT / (stem + ".txt")).exists() else ""
    m = re.search(r"SG&A, % от продаж\s+([-−]?[\d,\.]+%)\s+([-−]?[\d,\.]+%)", t)
    if m: return [m.group(1), m.group(2)]
    m = re.search(r"SG&A[^\n%]{0,60}?([-−]?[\d,\.]+%)", t)
    return [m.group(1)] if m else []


def deltas(stem):
    t = (TXT / (stem + ".txt")).read_text(encoding="utf-8") if (TXT / (stem + ".txt")).exists() else ""
    out = {}
    pats = {"personnel": r"[Рр]асходы на персонал[^\n%]{0,120}?(выросли|снизились|сократил[а-я]*|увеличил[а-я]*|уменьшил[а-я]*)[^\n%]{0,40}?на (\d+) б\. ?п",
            "utilities": r"коммунальные услуги[^\n%]{0,120}?(выросли|снизились|сократил[а-я]*|увеличил[а-я]*)[^\n%]{0,40}?на (\d+) б\. ?п",
            "repair": r"ремонт[^\n%]{0,120}?(выросли|снизились|сократил[а-я]*|увеличил[а-я]*)[^\n%]{0,40}?на (\d+) б\. ?п"}
    for k, pat in pats.items():
        ms = re.findall(pat, t)
        if ms:
            out[k] = [(-v if d in ("снизились", "сократились", "сократился", "уменьшились") else v)
                      for d, v in [(a, int(b)) for a, b in ms[:4]]]
    m = re.search(r"программ[^\n]{0,40}лояльности[^\n]{0,80}?(\d+[,\.]\d+)\s*млн", t)
    if m: out["loyalty_m_cards"] = float(m.group(1).replace(",", "."))
    return out


PERSONNEL = {  # IFRS thousands->bn; H1 from interim notes
    "2024FY": 278.0, "2025FY": 328.5, "2025H1": 152.5, "2026H1": 181.1,
}
RENT_CASH = {"2024FY": 63.0, "2025FY": 57.0, "2025H1": 29.4, "2026H1": 30.5}  # lease principal paid (CF)
REV = {"2024FY": 3043.4, "2025FY": 3509.2, "2024H1": 1460.1, "2025H1": 1673.2, "2026H1": 1887.2}

FORMATS = [("conv", r"Магазины у дома «Магнит»"), ("dixy", r"Магазины у дома «ДИКСИ»"),
           ("drogerie", r"Дрогери\d?"), ("super", r"Супермаркеты\d?")]


def format_revenue(stem):
    t = (TXT / (stem + ".txt")).read_text(encoding="utf-8") if (TXT / (stem + ".txt")).exists() else ""
    t = re.sub(r"(Дрогери|Супермаркеты|Магнит»|ДИКСИ»)(\d+)", r"\1", t)  # footnote digit glued to label
    out = {}
    for key, pat in FORMATS:
        m = re.search(pat, t)
        if not m: continue
        chunk = t[m.start():m.start() + 200]
        pct = re.search(r"([\d,\.]+)\s*%", chunk)
        if not pct: continue
        body = chunk[:pct.start()]  # row ends at its own % (never bleed into next row)
        toks = re.findall(r"\d+", body)
        yoy = float(pct.group(1).replace(",", "."))
        # layout cur/prev[/diff], each 1-3 groups; validate by reported yoy AND diff identity
        best = None
        n = len(toks)
        for i in (1, 2, 3):
            for j in (1, 2, 3):
                for k in (0, 1, 2, 3):
                    if i + j + k != n: continue
                    a = int("".join(toks[:i])); b = int("".join(toks[i:i + j]))
                    if b <= 0: continue
                    if abs(a / b * 100 - 100 - yoy) > 1.0: continue
                    if k:
                        dd = int("".join(toks[i + j:]))
                        if abs((a - b) - dd) > max(2, a * 0.002): continue
                    best = (a, b)
                    break
                if best: break
            if best: break
        if best:
            out[key] = {"cur_mln": best[0], "prev_mln": best[1], "yoy": yoy}
    return out

rows = []
for period, rev in REV.items():
    stem = {"2024FY": "2024_0", "2025FY": "2025_0", "2024H1": "2024_1",
            "2025H1": "2025_1", "2026H1": "2026_0"}[period] + "_press-release"
    r = {"period": period, "revenue": rev, "sga_pct": sga_pct(stem), "deltas_bps": deltas(stem)}
    if period in PERSONNEL:
        r["personnel"] = PERSONNEL[period]
        r["personnel_pct"] = round(PERSONNEL[period] / rev * 100, 2)
    if period in RENT_CASH:
        r["rent_cash"] = RENT_CASH[period]
        r["rent_cash_pct"] = round(RENT_CASH[period] / rev * 100, 2)
    r["formats_mln"] = format_revenue(stem)
    rows.append(r)
    print(period, "rev", rev, "| personnel", r.get("personnel"), f"({r.get('personnel_pct')}%)",
          "| rent", r.get("rent_cash"), "| sga", r["sga_pct"], "| deltas", r["deltas_bps"])

# H1 gross->ebitda wedge check (audit §6), in BASIS POINTS
g = {(x["series"], x["period"]): x["value"] for x in reg if x.get("basis") == "pre16" and x["status"] == "ok"}
for a, b in (("2025H1", "2026H1"),):
    gm = (g[("gross_profit", b)] / REV[b] - g[("gross_profit", a)] / REV[a]) * 10000
    em = (g[("ebitda", b)] / REV[b] - g[("ebitda", a)] / REV[a]) * 10000
    print(f"wedge {a}->{b}: gross {gm:+.0f}bp, ebitda {em:+.0f}bp, absorbed {gm-em:+.0f}bp")
    rows.append({"period": f"{a}->{b} wedge_check", "gross_bp": round(gm), "ebitda_bp": round(em),
                 "absorbed_bp": round(gm - em)})

(DATA / "opex_bridge.json").write_text(json.dumps(
    {"rows": rows, "method": "levels where disclosed; component bps deltas otherwise (levels undisclosed)",
     " Labor_note": "personnel IFRS FY + H1 notes; rent = lease principal CF; logistics mostly in COGS per press"},
    ensure_ascii=False, indent=1), encoding="utf-8")
print("saved opex_bridge.json")
