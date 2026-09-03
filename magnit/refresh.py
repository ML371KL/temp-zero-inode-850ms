"""Orchestrator: staged refresh with freshness SLA + red-run fail-closed rule.
Stages run as subprocesses (no refactor risk). Critical-stage failure -> STOP,
previous outputs untouched (fail closed), run log records red.
Usage: .venv\\Scripts\\python.exe magnit\\refresh.py [--only market,macro] [--dry-run]
"""
import subprocess, sys, json, pathlib, datetime, os

ROOT = pathlib.Path(__file__).parent
PY = sys.executable  # .venv python when invoked via .venv
DATA = ROOT / "data"

# sla_hours: max acceptable age of stage outputs before stage must re-run green
STAGES = [
    {"name": "catalog", "cmd": [PY, "magnit/parse_ir_catalog.py"], "critical": True, "sla_hours": 24 * 7,
     "outputs": ["data/ir_catalog.json"]},
    {"name": "market", "cmd": [PY, "magnit/market_snapshot.py"], "critical": True, "sla_hours": 24,
     "outputs": ["data/market/latest.json"]},
    {"name": "macro", "cmd": [PY, "magnit/refresh_macro.py"], "critical": True, "sla_hours": 24 * 8,
     "outputs": ["data/macro/food_weekly.json", "data/macro/key_rate.json"]},
    {"name": "peers", "cmd": [PY, "magnit/download_peers_macro.py"], "critical": False, "sla_hours": 24 * 30,
     "outputs": ["data/peers/x5_quarterly.json"]},
    {"name": "parse", "cmd": [PY, "magnit/parse_history.py"], "critical": True, "sla_hours": 24 * 90,
     "outputs": ["data/registry.json"]},
    {"name": "skill", "cmd": [PY, "magnit/track_skill.py"], "critical": False, "sla_hours": 24 * 30,
     "outputs": ["data/skill_v1.json"]},
    {"name": "fv", "cmd": [PY, "magnit/fv_distribution.py"], "critical": True, "sla_hours": 24 * 8,
     "outputs": ["data/fv_dist.json"]},
    {"name": "decision", "cmd": [PY, "magnit/decision_layer.py"], "critical": False, "sla_hours": 24 * 8,
     "outputs": []},
    {"name": "snapshot", "cmd": [PY, "magnit/snapshot_registry.py"], "critical": False, "sla_hours": 24 * 8,
     "outputs": []},
    {"name": "report", "cmd": [PY, "magnit/build_report.py"], "critical": False, "sla_hours": 24 * 8,
     "outputs": ["data/report.md"]},
]

REPO = pathlib.Path(__file__).parent.parent  # repo root (portable: local checkout or /srv/dash/repo-850)

def fresh(path, sla_h):
    """Check output freshness by mtime relative to repo root."""
    c = REPO / path
    if not c.exists():
        return False, None
    age_h = (datetime.datetime.now().timestamp() - c.stat().st_mtime) / 3600
    return age_h <= sla_h, round(age_h, 1)

def main():
    only = set(os.environ.get("STAGES", "").split(",")) if os.environ.get("STAGES") else None
    dry = "--dry-run" in sys.argv
    arg_only = [a for a in sys.argv[1:] if not a.startswith("--")]
    if arg_only: only = set(",".join(arg_only).split(","))
    log = {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "stages": [], "status": "green"}
    runs = DATA / "runs"
    runs.mkdir(exist_ok=True)
    for st in STAGES:
        if only and st["name"] not in only: continue
        ok_out = all(fresh(o, st["sla_hours"])[0] for o in st["outputs"]) if st["outputs"] else True
        rec = {"stage": st["name"], "critical": st["critical"]}
        if dry:
            rec.update({"mode": "dry-run", "outputs_fresh": ok_out})
            log["stages"].append(rec); continue
        r = subprocess.run(st["cmd"], cwd=str(REPO),
                           capture_output=True, text=True, timeout=900)
        rec.update({"rc": r.returncode, "tail": (r.stdout or "")[-400:], "stderr": (r.stderr or "")[-400:]})
        log["stages"].append(rec)
        print(f"[{st['name']}] rc={r.returncode}")
        if r.returncode != 0:
            print((r.stdout or "")[-800:]); print((r.stderr or "")[-800:])
            if st["critical"]:
                log["status"] = "red"
                break
    if any(s.get("rc", 0) != 0 and not s["critical"] for s in log["stages"]):
        log["status"] = "amber" if log["status"] == "green" else log["status"]
    log["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    (runs / f"run_{stamp}_{log['status']}.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"run status: {log['status']} (log run_{stamp}_{log['status']}.json)")
    return 0 if log["status"] != "red" else 1

if __name__ == "__main__":
    sys.exit(main())
