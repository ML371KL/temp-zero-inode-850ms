"""Probe IFRS accountability PDFs: extract text, check if text-based, find key statements.
Saves magnit/data/ifrs_text/{stem}.txt + probe report.
"""
import json, pathlib, re
from pypdf import PdfReader

DATA = pathlib.Path(__file__).parent / "data"
PDFS = DATA / "pdfs"
OUT = DATA / "ifrs_text"
OUT.mkdir(parents=True, exist_ok=True)
manifest = json.loads((PDFS / "manifest.json").read_text(encoding="utf-8"))

TERMS = ["Активы", "Обязательства", "Аренда", "Запасы", "Выручка", "Амортизация",
         "Денежные средства", "Кредиты и займы", "Капитал", "Отчет о финансовом положении",
         "денежных средств", "Lease", "IFRS 16", "МСФО 16"]

for m in manifest:
    if m["kind"] != "accountability": continue
    f = PDFS / m["file"]
    rd = PdfReader(str(f))
    texts = [(p.extract_text() or "") for p in rd.pages]
    full = "\n".join(texts)
    stem = m["key"].replace(":", "_").replace("#", "_")
    (OUT / (stem + ".txt")).write_text(full, encoding="utf-8")
    nonEmpty = sum(1 for t in texts if t.strip())
    print(f"== {m['key']} pages={len(rd.pages)} text_pages={nonEmpty} chars={len(full)}")
    for term in TERMS:
        c = full.count(term)
        if c: print(f"   {term}: x{c}")
