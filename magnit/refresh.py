"""Orchestrator: staged refresh with freshness SLA + red-run fail-closed rule.
- Lock file prevents parallel runs (stale lock >3h is reaped).
- Pre-backup of key outputs; on red critical stage -> RESTORE (atomic fail-closed).
- pytest runs FIRST: red tests block everything (model-health gate; no ACT on red).
- Fresh outputs are skipped unless --force (SLA recorded in log either way).
- export stage rebuilds dashboard bundle; deploy stage runs only with MAGNIT_DEPLOY=1.
Usage: .venv\\Scripts\\python.exe magnit\\refresh.py [--only market,macro] [--dry-run] [--force]
"""
import subprocess, sys, json, pathlib, datetime, os, shutil, time

ROOT = pathlib.Path(__file__).parent
PY = sys.executable
DATA = ROOT / "data"

STAGES = [
    {"name": "tests", "cmd": [PY, "-m", "pytest", "magnit/tests", "-q"], "critical": True, "sla_hours": 0,
     "outputs": []},
    {"name": "catalog", "cmd": [PY, "magnit/parse_ir_catalog.py"], "critical": True, "sla_hours": 24 * 7,
     "outputs": ["magnit/data/ir_catalog.json"]},
    {"name": "market", "cmd": [PY, "magnit/market_snapshot.py"], "critical": True, "sla_hours": 24,
     "outputs": ["magnit/data/market/latest.json"]},
    {"name": "macro", "cmd": [PY, "magnit/refresh_macro.py"], "critical": True, "sla_hours": 24 * 8,
     "outputs": ["magnit/data/macro/food_weekly.json", "magnit/data/macro/key_rate.json"]},
    {"name": "peers", "cmd": [PY, "magnit/download_peers_macro.py"], "critical": False, "sla_hours": 24 * 30,
     "outputs": ["magnit/data/peers/x5_quarterly.json"]},
    {"name": "parse", "cmd": [PY, "magnit/parse_history.py"], "critical": True, "sla_hours": 24 * 90,
     "outputs": ["magnit/data/registry.json"]},
    {"name": "restatements", "cmd": [PY, "magnit/check_restatements.py"], "critical": False, "sla_hours": 24 * 30,
     "outputs": ["magnit/data/restatements.json"]},
    {"name": "skill", "cmd": [PY, "magnit/track_skill.py"], "critical": False, "sla_hours": 24 * 30,
     "outputs": ["magnit/data/skill_lfl.json"]},
    {"name": "opex", "cmd": [PY, "magnit/opex_bridge.py"], "critical": False, "sla_hours": 24 * 30,
     "outputs": ["magnit/data/opex_bridge.json"]},
    {"name": "fv", "cmd": [PY, "magnit/fv_distribution.py"], "critical": True, "sla_hours": 24 * 8,
     "outputs": ["magnit/data/fv_dist.json"]},
    {"name": "sensitivity", "cmd": [PY, "magnit/sensitivity_audit.py"], "critical": False, "sla_hours": 24 * 8,
     "outputs": ["magnit/data/sensitivity.json"]},
    {"name": "decision", "cmd": [PY, "magnit/decision_layer.py"], "critical": True, "sla_hours": 24 * 8,
     "outputs": ["magnit/data/decision.json"]},
    {"name": "snapshot", "cmd": [PY, "magnit/snapshot_registry.py"], "critical": False, "sla_hours": 24 * 8,
     "outputs": []},
    {"name": "report", "cmd": [PY, "magnit/build_report.py"], "critical": False, "sla_hours": 24 * 8,
     "outputs": ["magnit/data/report.md"]},
    {"name": "export", "cmd": [PY, "magnit/export_dashboard.py"], "critical": False, "sla_hours": 24 * 8,
     "outputs": []},
]
if os.environ.get("MAGNIT_DEPLOY") == "1":
    # local machine only: wrangler OAuth of the interactive user; never on shared runners
    STAGES.append({"name": "deploy", "cmd": ["powershell", "-ExecutionPolicy", "Bypass", "-File",
                                             "C:/Users/rodio/Documents/magnit-850ms/deploy.ps1"],
                   "critical": False, "sla_hours": 24 * 8, "outputs": []})

REPO = pathlib.Path(__file__).parent.parent
BACKUP_KEYS = ["magnit/data/registry.json", "magnit/data/fv_dist.json", "magnit/data/skill_v1.json",
               "magnit/data/decision.json", "magnit/data/report.md", "magnit/data/alerts.json",
               "magnit/data/sensitivity.json"]


def fresh(path, sla_h):
    c = REPO / path
    if not c.exists():
        return False, None
    age_h = (datetime.datetime.now().timestamp() - c.stat().st_mtime) / 3600
    return age_h <= sla_h, round(age_h, 1)


def acquire_lock(runs):
    lock = runs / "refresh.lock"
    if lock.exists():
        try:
            pid, ts = lock.read_text().split(":")
            if time.time() - float(ts) < 3 * 3600:
                return None  # live lock held
        except Exception:
            pass
    lock.write_text(f"{os.getpid()}:{time.time()}")
    return lock


def main():
    only = set(os.environ.get("STAGES", "").split(",")) if os.environ.get("STAGES") else None
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args: only = set(",".join(args).split(","))
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    log = {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "stages": [], "status": "green"}
    runs = DATA / "runs"
    runs.mkdir(exist_ok=True)
    if dry:
        for st in STAGES:
            if only and st["name"] not in only: continue
            ok_out = all(fresh(o, st["sla_hours"])[0] for o in st["outputs"]) if st["outputs"] else True
            log["stages"].append({"stage": st["name"], "critical": st["critical"],
                                  "mode": "dry-run", "outputs_fresh": ok_out})
        print(f"dry-run ok ({len(log['stages'])} stages listed)")
        return 0
    lock = acquire_lock(runs)
    if lock is None:
        print("another refresh holds the lock; exiting")
        return 2
    # pre-backup key outputs for atomic fail-closed restore
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    bdir = runs / f"backup_{stamp}"
    bdir.mkdir(exist_ok=True)
    for rel in BACKUP_KEYS:
        src = REPO / rel
        if src.exists():
            shutil.copy2(src, bdir / pathlib.Path(rel).name)
    try:
        for st in STAGES:
            if only and st["name"] not in only: continue
            is_fresh = all(fresh(o, st["sla_hours"])[0] for o in st["outputs"]) if st["outputs"] else False
            rec = {"stage": st["name"], "critical": st["critical"], "outputs_fresh_before": is_fresh}
            if is_fresh and not force and st["name"] not in ("tests",):
                rec.update({"skipped": True})
                log["stages"].append(rec)
                print(f"[{st['name']}] skipped (fresh)")
                continue
            r = subprocess.run(st["cmd"], cwd=str(REPO), capture_output=True, text=True, timeout=900)
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
        if log["status"] == "red":
            for rel in BACKUP_KEYS:  # atomic fail-closed: restore last-good
                src = bdir / pathlib.Path(rel).name
                if src.exists():
                    shutil.copy2(src, REPO / rel)
            log["restored_from"] = bdir.name
            print(f"RED: restored last-good outputs from {bdir.name}")
    finally:
        try: lock.unlink()
        except OSError: pass
    log["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (runs / f"run_{stamp}_{log['status']}.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"run status: {log['status']} (log run_{stamp}_{log['status']}.json)")
    return 0 if log["status"] != "red" else 1


if __name__ == "__main__":
    sys.exit(main())
