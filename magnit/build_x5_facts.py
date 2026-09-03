"""X5 peer facts (primary source PDFs in magnit/data/peers/), manually verified with snippets.
released_at = X5 publication dates (trading updates lead Magnit by 2-6 weeks).
Saves magnit/data/peers/x5_facts.json
"""
import json, pathlib

FACTS = [
    # period, series, value, unit, released_at, source file, note
    ("FY2024", "x5_revenue_yoy", 24.2, "pct", "2025-01-28", "x5_q4_2024_trading.pdf", "net revenue FY2024; Magnit +19.6 -> gap -4.6pp"),
    ("FY2025", "x5_revenue_yoy", 18.8, "pct", "2026-01-22", "x5_q4_2025_trading.pdf", "revenue FY2025; Magnit +15.3 -> gap -3.5pp"),
    ("2025-Q4", "x5_pyaterochka_yoy", 13.2, "pct", "2026-01-22", "x5_q4_2025_trading.pdf", "net retail revenue"),
    ("2025-Q4", "x5_pyaterochka_lfl", 7.3, "pct", "2026-01-22", "x5_q4_2025_trading.pdf", "LFL traffic +0.6pp"),
    ("2025-Q4", "x5_perekrestok_yoy", 5.8, "pct", "2026-01-22", "x5_q4_2025_trading.pdf", ""),
    ("2025-Q4", "x5_perekrestok_lfl", 4.8, "pct", "2026-01-22", "x5_q4_2025_trading.pdf", "ticket-driven"),
    ("2026-Q1", "x5_revenue_yoy", 11.3, "pct", "2026-04-16", "x5_q1_2026_trading.pdf", "Magnit Q1 +13.1 (rel 30Apr) -> Magnit AHEAD +1.8pp"),
    ("2026-Q1", "x5_pyaterochka_yoy", 9.9, "pct", "2026-04-16", "x5_q1_2026_trading.pdf", "LFL +6.0 (ticket)"),
    ("2026-Q1", "x5_perekrestok_yoy", 6.8, "pct", "2026-04-16", "x5_q1_2026_trading.pdf", "LFL +6.7 (ticket)"),
    ("2026-Q2", "x5_revenue_yoy", 9.9, "pct", "2026-07-16", "x5_q2_2026_trading.pdf", "Magnit 1H +12.8 (rel 28Aug) -> Magnit ahead again"),
    ("2026-Q2", "x5_pyaterochka_yoy", 7.6, "pct", "2026-07-16", "x5_q2_2026_trading.pdf", "LFL +3.9 (ticket +2.8, traffic +1.1)"),
    ("2026-Q2", "x5_perekrestok_yoy", 6.5, "pct", "2026-07-16", "x5_q2_2026_trading.pdf", "LFL +5.2 (ticket +3.6, traffic +1.6)"),
    ("2026-Q1", "x5_fin_date", None, "", "2026-04-29", "x5_q1_2026_fin.pdf", "financials 13d after trading; Magnit FY25 next day 30Apr"),
    ("2026-Q2", "x5_fin_date", None, "", "2026-08-13", "x5_q2_2026_fin.pdf", "financials 15d before Magnit 1H (28Aug)"),
]
rows = [{"period": p, "series": s, "value": v, "unit": u, "released_at": r,
         "source": "x5.ru IR (primary)", "file": f, "note": n}
        for p, s, v, u, r, f, n in FACTS]
pathlib.Path("magnit/data/peers/x5_facts.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"saved {len(rows)} X5 facts")
print("lead-lag: X5 Q2 trading 16Jul -> Magnit 1H 28Aug = 43 days; X5 Q1 trading 16Apr -> Magnit 30Apr = 14 days")
