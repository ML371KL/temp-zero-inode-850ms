"""Vintage control: append-only snapshots of registry + key inputs.
Each run writes magnit/data/vintages/registry_YYYYMMDD-HHMMSS.json with meta
(source shas, row counts, status mix) + diff summary vs previous snapshot.
Rule: builders may only append new vintages; history is never rewritten in place
(except documented supersede with vintage bump, as done v1->v7).
"""
import json, pathlib, hashlib, datetime

DATA = pathlib.Path(__file__).parent / "data"
VDIR = DATA / "vintages"
VDIR.mkdir(exist_ok=True)

def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]

def main():
    reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    from collections import Counter
    mix = Counter(x["status"] for x in reg)
    periods = sorted({x["period"] for x in reg})
    meta = {"stamp_utc": stamp,
            "rows": len(reg), "status_mix": dict(mix), "periods": periods,
            "inputs": {}}
    for f in ["registry.json", "pnl.json", "organic.json", "ifrs_facts.json",
              "macro/food_weekly.json", "macro/food_monthly.json", "macro/key_rate.json",
              "macro/wacc.json", "peers/x5_facts.json", "peers/mult_history.json",
              "fv_dist.json", "fv_v1.json", "calibration_report_v1.json"]:
        p = DATA / f
        if p.exists(): meta["inputs"][f] = sha(p)
    man = json.loads((DATA / "pdfs" / "manifest.json").read_text(encoding="utf-8"))
    meta["pdf_manifest_entries"] = len(man)
    (VDIR / f"registry_{stamp}.json").write_text(
        json.dumps({"meta": meta, "rows": reg}, ensure_ascii=False, indent=1), encoding="utf-8")
    # diff vs previous
    prev = sorted(VDIR.glob("registry_*.json"))
    if len(prev) > 1:
        old = json.loads(prev[-2].read_text(encoding="utf-8"))
        oldk = {(x["series"], x["period"], x.get("basis", "")) for x in old["rows"]}
        newk = {(x["series"], x["period"], x.get("basis", "")) for x in reg}
        chg = [x for x in reg if (x["series"], x["period"], x.get("basis", "")) not in oldk]
        print(f"snapshot {stamp}: rows {len(reg)} (+{len(newk-oldk)} keys, {len(chg)} new rows)")
    else:
        print(f"baseline snapshot {stamp}: rows {len(reg)}, periods {len(periods)}")
    print("status:", dict(mix))

if __name__ == "__main__":
    main()
