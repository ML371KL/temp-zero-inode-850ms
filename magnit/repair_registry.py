"""One-off data repair (root causes already fixed in builders):
1. drop v5 Q4-misattributed FY rows (2022FY/2023FY gross/ebitda/retail)
2. drop buggy v6 rows (growth stored as level, basis None)
3. clamp future released_at to today
"""
import json, pathlib, datetime

P = pathlib.Path("magnit/data/registry.json")
reg = json.loads(P.read_text(encoding="utf-8"))
today = datetime.date.today().isoformat()
n0 = len(reg)
reg = [x for x in reg if not (
    (x.get("vintage") == "v5-history" and (x["series"], x["period"]) in
     {("gross_profit", "2022FY"), ("ebitda", "2022FY"), ("retail_revenue", "2022FY"),
      ("gross_profit", "2023FY"), ("ebitda", "2023FY"), ("retail_revenue", "2023FY")})
    or (x.get("vintage") == "v6-fy-narrative" and x["series"] in ("gross_profit", "retail_revenue")
        and not x.get("basis")))]
n1 = len(reg)
fixed_dates = 0
for x in reg:
    if x["released_at"] > today:
        x["released_at"] = today
        fixed_dates += 1
P.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"dropped {n0-n1} stale rows; clamped {fixed_dates} future dates (today={today}); total {len(reg)}")
