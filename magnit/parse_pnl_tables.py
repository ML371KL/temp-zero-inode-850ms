"""Parse structured P&L + debt tables from press-release texts (primary source).
Table rows: 'EBITDA 169 276 171 897 -1,5% 306 162 290 935 5,2%' =
  cur_pre, prev_pre, yoy | cur_post, prev_post, yoy_post.
Segment at %-tokens, then split digit-group runs (4 groups->2+2, 6->3+3).
Saves magnit/data/pnl.json with audit snippets.
"""
import re, json, pathlib

DATA = pathlib.Path(__file__).parent / "data"
TXT = DATA / "press_text"
PCT = re.compile(r"(-?\d{1,3},\d+)\s*%")

def split_groups(groups: list[str]) -> list[int]:
    n = len(groups)
    if n <= 3: return [int("".join(groups))]
    if n == 4: return [int("".join(groups[:2])), int("".join(groups[2:]))]
    if n == 6: return [int("".join(groups[:3])), int("".join(groups[3:]))]
    if n == 5:
        a, b = ("".join(groups[:3]), "".join(groups[3:])), ("".join(groups[:2]), "".join(groups[2:]))
        pick = a if abs(len(a[0]) - len(a[1])) <= abs(len(b[0]) - len(b[1])) else b
        return [int(pick[0]), int(pick[1])]
    return [int("".join(groups))]

def parse_row(chunk: str):
    """Return (numbers_with_pcts_in_order, snippet)."""
    parts, pos, seq = [], 0, []
    for m in PCT.finditer(chunk):
        seg = chunk[pos:m.start()]
        groups = re.findall(r"\d{3}|\d{1,3}", seg)
        # keep only groups that form thousand-runs: filter stray single digits from words? keep simple:
        grp3 = [g for g in re.findall(r"\d+", seg)]
        flat = []
        for g in grp3: flat.extend([g[i:i+3] for i in range(0, len(g), 3)] if len(g) > 3 else [g])
        # Actually simpler: collect raw digit tokens in order
        toks = re.findall(r"\d+", seg)
        # merge: consecutive 3-digit tokens belong together; split runs at non-space separators already handled
        nums = split_groups(toks) if toks else []
        seq.extend(nums)
        seq.append(m.group(1) + "%")
        pos = m.end()
    return seq

def find_row(table: str, label_pat: str):
    best = None
    for m in re.finditer(label_pat, table):
        chunk = table[m.start():m.start() + 150]
        seq = parse_row(chunk)
        big = [x for x in seq if isinstance(x, int) and x > 20000]
        if best is None or len(big) > len(best[1]):
            best = (chunk[:100].replace("\n", " "), big, seq)
    if best and len(best[1]) >= 2:
        return best[2]
    return []

def parse_pnl(text):
    i0, i1 = text.find("бщая выручка"), text.find("истая прибыль / убыток")
    table = text[i0:i1 + 400] if i0 != -1 and i1 != -1 else text
    out = {}
    for key, pat in {"revenue_total": r"бщая выручка",
                     "retail_revenue": r"истая розничная выручка",
                     "gross_profit": r"аловая прибыль",
                     "ebitda": r"\bEBITDA\b",
                     "ebit": r"\bEBIT\b"}.items():
        seq = find_row(table, pat)
        # group into (num,num,pct) triplets, drop consecutive dups (bleed from adjacent rows)
        trips, i = [], 0
        while i + 2 < len(seq):
            a, b, c = seq[i], seq[i+1], seq[i+2]
            if isinstance(a, int) and isinstance(b, int) and isinstance(c, str):
                trips.append([a, b, c]); i += 3
            else:
                i += 1
        uniq = [t for j, t in enumerate(trips) if j == 0 or t != trips[j-1]]
        if uniq: out[key] = uniq[0] if key in ("revenue_total", "retail_revenue") else (uniq[:2] if len(uniq) > 1 else uniq)
    m = re.search(r"истая прибыль / убыток(.{0,120}?)", text, re.S)
    if m:
        chunk = m.group(1)
        pm = PCT.search(chunk)
        toks = re.findall(r"\d+", chunk[:pm.start()] if pm else chunk)
        nums = split_groups(toks) if toks else []
        yoy = pm.group(1) + "%" if pm else ""
        if len(nums) >= 2:
            neg = chunk.strip().startswith("-")
            out["net_income"] = [-nums[0] if neg else nums[0], nums[1], yoy]
    for k, pat in {"gross_margin": r"валовая маржа, %\s+([\d,\.]+%)\s+([\d,\.]+%)",
                   "ebitda_margin": r"EBITDA маржа, %\s+([\d,\.]+%)\s+([\d,\.]+%)"}.items():
        mm = re.search(pat, text)
        if mm: out[k] = [mm.group(1), mm.group(2)]
    debt = {}
    nd = re.findall(r"чистый долг, млрд руб\.\s+([\d\s]+[,\.]\d)\s+([\d\s]+[,\.]\d)", text, re.I)
    if nd: debt["net_debt_pairs"] = [(a.replace(" ", ""), b.replace(" ", "")) for a, b in nd]
    ndx = re.findall(r"чистый долг/EBITDA\s+([\d,\.]+)x\s+([\d,\.]+)x", text, re.I)
    if ndx: debt["nd_ebitda_pairs"] = ndx
    cod = re.search(r"стоимость долга.{0,120}?до ([\d,\.]+%)", text)
    cx = re.search(r"[Кк]апитальные затраты.{0,220}?составили ([\d,\.]+)\s*млрд", text, re.S)
    return {"table": out, "debt": debt,
            "cost_of_debt": cod.group(0)[:160] if cod else "",
            "capex": (cx.group(0)[:200].replace("\n", " ") if cx else "")}

def main():
    allp = {}
    for f in sorted(TXT.glob("*.txt")):
        allp[f.stem] = parse_pnl(f.read_text(encoding="utf-8"))
        print(f"== {f.stem} ==")
        for k, v in allp[f.stem]["table"].items(): print(f"  {k}: {v}")
        print(f"  debt: {allp[f.stem]['debt']}")
        print(f"  cod: {allp[f.stem]['cost_of_debt'][:90]}")
        print(f"  capex: {allp[f.stem]['capex'][:120]}")
    (DATA / "pnl.json").write_text(json.dumps(allp, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved pnl.json")

if __name__ == "__main__":
    main()
