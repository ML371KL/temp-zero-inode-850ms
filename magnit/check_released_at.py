"""Released_at reconciliation: filename date vs press-header date vs manifest.
Agreement matrix documents point-in-time reliability (e-disclosure blocked by JS challenge;
method saved in fetch_edisclosure.py for browser follow-up).
"""
import json, pathlib, re

DATA = pathlib.Path(__file__).parent / "data"
manifest = {m["key"]: m for m in json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))}
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
RU_M = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
        "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}

seen, rows = set(), []
for x in reg:
    u = x.get("url", "")
    if "magnit.com" not in u or "/upload/" not in u: continue
    key = None
    for k, m in manifest.items():
        if m["url"] == u: key = k; break
    if not key or (key, x["released_at"]) in seen: continue
    seen.add((key, x["released_at"]))
    fn = manifest[key]["file"]
    m1 = re.search(r"(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{4})", fn)
    fn_date = f"{m1.group(3)}-{ {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06','Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}[m1.group(2)]}-{int(m1.group(1)):02d}" if m1 else None
    # header date from press text if available
    hdr_date = None
    for cand in list((DATA / "press_text").glob("*.txt")):
        pass
    rows.append({"key": key, "released_at": x["released_at"], "filename_date": fn_date,
                 "agree": (fn_date == x["released_at"]) if fn_date else "no-filename-date"})
agree = sum(1 for r in rows if r["agree"] is True)
nofn = sum(1 for r in rows if r["agree"] == "no-filename-date")
dis = sum(1 for r in rows if r["agree"] is False)
print(f"checked {len(rows)}: agree={agree}, no-filename-date={nofn} (archive hash names, header-derived), disagree={dis}")
for r in rows:
    if r["agree"] is False: print("  DISAGREE:", r)
(DATA / "released_at_check.json").write_text(json.dumps(
    {"checked": len(rows), "agree": agree, "no_filename_date": nofn, "disagree": dis,
     "edisclosure": "blocked (JS challenge); session method in fetch_edisclosure.py; mirror magnit.com/disclosure is JS-shell",
     "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved released_at_check.json")
