"""Step 2a: extract key metrics from IR press-release PDFs (primary source).
Saves magnit/data/press_text/{key}.txt + extracted_facts.json with snippets for audit.
Regexes are RU/EN tolerant; every fact keeps (value, snippet, page) -> point-in-time safe.
"""
import re, json, pathlib
from pypdf import PdfReader

DATA = pathlib.Path(__file__).parent / "data"
PDFS = DATA / "pdfs"
TXT = DATA / "press_text"
TXT.mkdir(parents=True, exist_ok=True)

TARGETS = [m for m in json.loads((PDFS / "manifest.json").read_text(encoding="utf-8"))
           if m["kind"] == "press-release"]

PATTERNS = {
    "revenue": [r"выручк[аи][^\d]{0,40}(\d[\d\s]*[,\.]\d)\s*(млрд|млн)", r"revenue[^\d]{0,40}(\d[\d\s]*[,\.]\d)\s*(bn|mn)"],
    "revenue_yoy": [r"выручк[аи][^\n]{0,80}?(\d{1,2}[,\.]\d)\s*%", r"revenue[^\n]{0,80}?(\d{1,2}[,\.]\d)\s*%"],
    "lfl": [r"LFL[^\d%]{0,30}(\d{1,2}[,\.]\d)\s*%", r"сопоставим[^\n]{0,60}?(\d{1,2}[,\.]\d)\s*%"],
    "traffic": [r"трафик[^\d%\-+]{0,30}([+\-]?\d{1,2}[,\.]\d)\s*%", r"traffic[^\d%\-+]{0,30}([+\-]?\d{1,2}[,\.]\d)\s*%"],
    "ticket": [r"средн[^\n]{0,30}чек[^\d%\-+]{0,30}([+\-]?\d{1,2}[,\.]\d)\s*%", r"ticket[^\d%\-+]{0,30}([+\-]?\d{1,2}[,\.]\d)\s*%"],
    "stores": [r"магазин[^\d]{0,30}(\d{2}\s?\d{3})", r"stores[^\d]{0,30}(\d{2},?\d{3})"],
    "space": [r"торгов[^\d]{0,30}(\d{2}\s?\d{3})", r"selling space[^\d]{0,30}(\d{2},?\d{3})"],
    "ebitda_margin": [r"EBITDA[^\d%]{0,60}?(\d{1,2}[,\.]\d)\s*%", r"рентабельност[^\n]{0,20}EBITDA[^\d%]{0,20}(\d{1,2}[,\.]\d)\s*%"],
    "gross_margin": [r"валов[^\d%]{0,60}?(\d{2}[,\.]\d)\s*%", r"gross margin[^\d%]{0,20}(\d{2}[,\.]\d)\s*%"],
    "net_debt_ebitda": [r"долг\s*/\s*EBITDA[^\d]{0,20}(\d[,\.]\d)\s*x", r"Net Debt\s*/\s*EBITDA[^\d]{0,20}(\d[,\.]\d)\s*x"],
    "capex": [r"капитальн[^\d]{0,40}(\d{2,3}[,\.]\d?)\s*(млрд|млн)", r"capex[^\d]{0,40}(\d{2,3}[,\.]\d?)\s*(bn|mn)"],
}

def num(s: str) -> float:
    return float(s.replace(" ", "").replace("\u00a0", "").replace(",", "."))

def main():
    facts = []
    for m in TARGETS:
        f = PDFS / m["file"]
        rd = PdfReader(str(f))
        pages = [(i, (p.extract_text() or "")) for i, p in enumerate(rd.pages)]
        full = "\n".join(t for _, t in pages)
        (TXT / (m["key"].replace(":", "_").replace("#", "_") + ".txt")).write_text(full, encoding="utf-8")
        for series, pats in PATTERNS.items():
            for pat in pats:
                for mt in re.finditer(pat, full, re.I | re.S):
                    val = mt.group(1)
                    try: v = num(val)
                    except ValueError: continue
                    s0 = max(0, mt.start() - 120)
                    snip = re.sub(r"\s+", " ", full[s0:mt.end() + 60])[:220]
                    facts.append({"key": m["key"], "period": m["period"][:100], "series": series,
                                  "value_raw": val, "value": v, "snippet": snip, "url": m["url"]})
                    break  # first hit per pattern
    # dedupe: keep first per (key,series)
    seen, out = set(), []
    for f in facts:
        k = (f["key"], f["series"])
        if k in seen: continue
        seen.add(k); out.append(f)
    (DATA / "extracted_facts.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"press releases parsed: {len(TARGETS)}, facts: {len(out)}")
    for f in out:
        print(f"  {f['key']} {f['series']:<14} {f['value']:<12} | {f['snippet'][:110]}")

if __name__ == "__main__":
    main()
