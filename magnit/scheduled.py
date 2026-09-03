"""Wrapper for scheduled runs: refresh market daily, macro weekly, full monthly.
Logs to magnit/data/runs/sched_*.log. Called by Windows Task Scheduler (see register_scheduler.ps1).
Usage: python magnit/scheduled.py [daily|weekly|monthly]
"""
import subprocess, sys, datetime, pathlib

ROOT = pathlib.Path(__file__).parent.parent  # repo root (portable)
LOGD = ROOT / "magnit" / "data" / "runs"

JOBS = {
    # times are SGT (machine TZ, MSK+5): daily 00:15 SGT = 19:15 MSK post-close;
    # weekly Mon 08:00 SGT + Thu 04:00 SGT (= Wed 23:00 MSK, after Rosstat weekly ~19:00 MSK)
    "daily": [["magnit/refresh_macro.py"], ["magnit/market_snapshot.py"], ["magnit/build_report.py"]],
    "weekly": [["magnit/refresh_macro.py"], ["magnit/market_snapshot.py"],
               ["magnit/watch_x5.py"], ["magnit/nowcast_q3.py"], ["magnit/build_report.py"]],
    "monthly": [["magnit/refresh.py"]],
}

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    logf = LOGD / f"sched_{mode}_{ts}.log"
    LOGD.mkdir(parents=True, exist_ok=True)
    with open(logf, "w", encoding="utf-8") as lf:
        lf.write(f"sched {mode} start {ts}\n")
        rc_all = 0
        for cmd in JOBS[mode]:
            r = subprocess.run([sys.executable] + cmd, cwd=str(ROOT),
                               capture_output=True, text=True, timeout=1800)
            lf.write(f"### {' '.join(cmd)} rc={r.returncode}\n{(r.stdout or '')[-600:]}\n{(r.stderr or '')[-600:]}\n")
            print(f"[{cmd[0]}] rc={r.returncode}")
            if r.returncode != 0:
                rc_all = 1
                if cmd[0] == "magnit/refresh.py":
                    break
        lf.write(f"done rc={rc_all}\n")
    print(f"log: {logf.name} rc={rc_all}")
    return rc_all

if __name__ == "__main__":
    sys.exit(main())
