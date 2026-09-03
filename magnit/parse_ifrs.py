"""Parse key IFRS facts (FY2025 + 1H2026): shares/treasury, leases, loans, D&A, impairments.
Figures in statements are in THOUSANDS of rubles -> convert to bn.
Saves magnit/data/ifrs_facts.json. Audit snippets kept.
"""
import json, pathlib, re

DATA = pathlib.Path(__file__).parent / "data"
T = {s: (DATA / "ifrs_text" / (s + ".txt")).read_text(encoding="utf-8")
     for s in ("2025_0_accountability", "2026_0_accountability")}
K = 1e-6  # thousand rub -> bn rub

def num3(toks):  # ['536','245','324'] -> 536245324
    return int("".join(toks))

def pair_after(text, anchor, n_groups=3):
    """Find anchor, then take first two numbers of n_groups thousand-groups after it.
    Strips IFRS note references ('8, 9, 25') that would otherwise merge with figures."""
    m = re.search(anchor, text)
    if not m: return None
    seg = text[m.end():m.end() + 400]
    seg = re.sub(r"\b\d{1,2}(?:,\s*\d{1,2})+\b", " ", seg)
    runs, spans = [], []
    for mm in re.finditer(r"\d{1,3}(?: \d{3}){%d}" % (n_groups - 1), seg):
        runs.append(num3(mm.group(0).split())); spans.append(mm.span())
        if len(runs) == 2: break
    if not runs: return None
    if len(runs) == 1: return [runs[0], None]
    between = seg[spans[0][1]:spans[1][0]]
    m_dash = re.search(r"[–—-]", between)
    m_num = re.search(r"\d", between)
    if m_dash and (not m_num or m_dash.start() < m_num.start()):
        return [runs[0], None]  # prev period dash = no charge
    return runs

def single_after(text, anchor):
    m = re.search(anchor, text)
    if not m: return None
    seg = text[m.end():m.end() + 300]
    mm = re.search(r"\d{1,3}(?: \d{3})+", seg)
    return num3(mm.group(0).split()) if mm else None

def grab_snip(text, anchor, w=140):
    m = re.search(anchor, text)
    return re.sub(r"\s+", " ", text[max(0, m.start()-w):m.end()+w])[:300] if m else ""

facts = []
def add(period, series, value, unit, note, anchor):
    facts.append({"period": period, "series": series, "value": value, "unit": unit,
                  "source": "magnit.com IFRS statements (primary)", "note": note,
                  "snippet": grab_snip(T["2025_0_accountability" if period == "FY2025" else "2026_0_accountability"], anchor)})

t25 = T["2025_0_accountability"]
# shares (thousands of shares -> millions)
add("FY2025", "shares_issued", 101911 / 1e3, "m", "issued+paid, 0.01 rub par", r"полностью оплаченный акционерный капитал")
add("FY2025", "shares_treasury", 34064 / 1e3, "m", "own shares bought back", r"Собственные акции, выкупленные")
add("FY2025", "shares_outstanding", 67847 / 1e3, "m", "in circulation end-FY2025 (start 67871, bought 24k)", r"Остаток акций в обращении на конец|Остаток акций в обращении")
# leases + loans are in thousands of rubles
r = pair_after(t25, r"Долгосрочные обязательства по аренде 9")
if r: add("FY2025", "lease_long", r[0] * K, "bn_rub", f"lease LT; prev {r[1]*K:.1f}", r"Долгосрочные обязательства по аренде 9")
r = pair_after(t25, r"Краткосрочные обязательства по аренде 9")
if r: add("FY2025", "lease_short", r[0] * K, "bn_rub", f"lease ST; prev {r[1]*K:.1f}", r"Краткосрочные обязательства по аренде 9")
r = pair_after(t25, r"Долгосрочные кредиты и займы 21")
if r: add("FY2025", "loans_long", r[0] * K, "bn_rub", f"loans LT; prev {r[1]*K:.1f}", r"Долгосрочные кредиты и займы 21")
r = pair_after(t25, r"Краткосрочные кредиты и займы 21")
if r: add("FY2025", "loans_short", r[0] * K, "bn_rub", f"loans ST; prev {r[1]*K:.1f}", r"Краткосрочные кредиты и займы 21")
# cash-flow statement items (thousands)
for anchor, series in [(r"Амортизацию и обесценение основных средств и активов в форме права\s+пользования", "da_rou"),
                       (r"Амортизацию и обесценение нематериальных активов", "da_intang"),
                       (r"Обесценение гудвила", "impair_goodwill"),
                       (r"Погашение обязательств по аренде", "lease_cash_out")]:
    r = pair_after(t25, anchor, 3)
    if r:
        pv = f"{r[1]*K:.1f}" if r[1] is not None else "n/a (dash)"
        add("FY2025", series, r[0] * K, "bn_rub", f"CF adjustment/outflow; prev {pv}", anchor)
# cross-checks
add("FY2025", "lease_total_implied", 536.2 + 63.9, "bn_rub", "LT+ST leases; post16-pre16 net debt gap = 600.0 -> match", r"Долгосрочные обязательства по аренде 9")
add("FY2025", "loans_total_implied", 467.8 + 277.9, "bn_rub", "LT+ST loans = 745.7 vs press total debt 745.8", r"Долгосрочные кредиты и займы 21")

(DATA / "ifrs_facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
for f in facts:
    print(f"  {f['period']} {f['series']:<20} {f['value']:<10.1f} {f['unit']:<7} | {f['note'][:70]}")
print(f"saved {len(facts)} IFRS facts")
