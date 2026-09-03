#!/usr/bin/env bash
# Wrapper /usr/local/sbin/magnit — subcommands map to pipeline entry points.
# Env from /usr/local/etc/magnit/env (never overwritten by installer).
set -euo pipefail
ETC=/usr/local/etc/magnit/env
if [[ -f "$ETC" ]]; then set -a; . "$ETC"; set +a; fi
# dash home (/srv/dash) is shared and may not be writable: keep npm cache out of it
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/var/tmp/npm-magnit}"
REPO="${MAGNIT_REPO:-/srv/dash/repo-850}"
VENV="${MAGNIT_VENV:-/srv/dash/venv-magnit}"
PY="$VENV/bin/python"
cd "$REPO"
case "${1:-help}" in
  daily)    exec "$PY" magnit/scheduled.py daily ;;
  weekly)   exec "$PY" magnit/scheduled.py weekly ;;
  monthly)  exec "$PY" magnit/refresh.py ;;
  # NOTE: nowcast_q3.py is quarter-specific (valid through Nov 2026); generalize to
  # current-quarter tracker when Q3 fact lands (weekly job will fail closed otherwise).
  nowcast)  exec "$PY" magnit/nowcast_q3.py ;;
  deploy)   shift; "$PY" magnit/export_dashboard.py && npx -y wrangler@4.26.0 pages deploy web --project-name tzi-850ms --branch main --commit-message "${*:-scheduled deploy}" ;;
  selftest) exec "$PY" -m pytest magnit/tests -q ;;
  bootstrap) exec "$PY" magnit/refresh.py ;;
  *) echo "usage: magnit {daily|weekly|monthly|nowcast|deploy|selftest|bootstrap}"; exit 2 ;;
esac
