"""Fetch CBR key rate history (daily -> change points + quarterly/monthly averages).
Source: https://www.cbr.ru/hd_base/KeyRate/ (UniDbQuery). Saves magnit/data/macro/key_rate.json
"""
import urllib.request, urllib.parse, re, json, pathlib, datetime
from collections import defaultdict

OUT = pathlib.Path(__file__).parent / "data" / "macro"
url = ("https://www.cbr.ru/hd_base/KeyRate/?" + urllib.parse.urlencode({
    "UniDbQuery.Posted": "True", "UniDbQuery.From": "01.01.2019", "UniDbQuery.To": "03.09.2026"}))
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
t = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
rows = re.findall(r"<td[^>]*>\s*(\d{2}\.\d{2}\.\d{4})\s*</td>\s*<td[^>]*>\s*([\d,\.]+)\s*</td>", t)
daily = [(datetime.datetime.strptime(d, "%d.%m.%Y").date().isoformat(), float(v.replace(",", "."))) for d, v in rows]
daily.sort()
# change points
changes = [daily[0]]
for d, v in daily[1:]:
    if v != changes[-1][1]:
        changes.append((d, v))
by_q = defaultdict(list)
by_m = defaultdict(list)
for d, v in daily:
    dt = datetime.date.fromisoformat(d)
    by_q[f"{dt.year}-Q{(dt.month-1)//3+1}"].append(v)
    by_m[d[:7]].append(v)
qavg = {k: round(sum(v) / len(v), 2) for k, v in sorted(by_q.items())}
(OUT / "key_rate.json").write_text(json.dumps(
    {"daily_n": len(daily), "range": [daily[0][0], daily[-1][0]],
     "current": {"date": daily[-1][0], "value": daily[-1][1]},
     "changes": [{"date": d, "value": v} for d, v in changes],
     "quarterly_avg": qavg,
     "source": url.split("?")[0], "fetched_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()},
    ensure_ascii=False, indent=1), encoding="utf-8")
print(f"daily {len(daily)}, changes {len(changes)}, current {daily[-1]}")
print("last 8 changes:")
for d, v in changes[-8:]: print(f"  {d} {v}%")
print("quarterly avg 2024Q1..2026Q3:")
for k in ("2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4",
          "2026-Q1", "2026-Q2", "2026-Q3"):
    if k in qavg: print(f"  {k}: {qavg[k]}%")
