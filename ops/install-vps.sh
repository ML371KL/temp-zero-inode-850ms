#!/usr/bin/env bash
# Magnit FV pipeline installer for the house VPS. Idempotent: re-run = update.
# Follows repo-842 conventions: env never overwritten, CRLF normalized,
# shared /srv/dash untouched, dash-alert bridge reused, git reset --hard updates.
#
# Run:  sudo bash ops/install-vps.sh
# Needs: REPO_URL default points here (temp-zero-inode-850ms).
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/ML371KL/temp-zero-inode-850ms.git}"
REPO_DIR="${REPO_DIR:-/srv/dash/repo-850}"
RUN_USER="${RUN_USER:-dash}"
ETC_DIR=/usr/local/etc/magnit
VENV_DIR="${VENV_DIR:-/srv/dash/venv-magnit}"
UNITS=(magnit-daily magnit-weekly magnit-monthly)

say() { printf '\n== %s\n' "$*"; }
note() { printf '   %s\n' "$*"; }

[[ $EUID -eq 0 ]] || { echo "need root: sudo bash ops/install-vps.sh" >&2; exit 1; }
src_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

missing=()
for cmd in git curl flock systemctl runuser install python3; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done
if (( ${#missing[@]} )); then echo "missing: ${missing[*]} (apt install git curl util-linux)" >&2; exit 1; fi

say "user $RUN_USER"
if id -u "$RUN_USER" >/dev/null 2>&1; then note "exists (uid $(id -u "$RUN_USER"))";
else useradd --system --home-dir /srv/dash --shell /usr/sbin/nologin "$RUN_USER"; note "created"; fi
[[ -d /srv/dash ]] && note "/srv/dash exists — permissions untouched (shared)" \
  || install -d -m 755 -o "$RUN_USER" -g "$RUN_USER" /srv/dash

say "node (wrangler Pages deploy)"
if command -v node >/dev/null 2>&1; then note "$(node -V 2>&1) present";
else
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null
  apt-get install -y -qq nodejs
  note "$(node -V 2>&1) installed"
fi

say "venv $VENV_DIR (pandas/numpy/openpyxl/pypdf/requests/pytest)"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  runuser -u "$RUN_USER" -- python3 -m venv "$VENV_DIR"
  note "created"
fi
# shellcheck disable=SC1091
runuser -u "$RUN_USER" -- "$VENV_DIR/bin/pip" install -q --upgrade pip
note "pip ready (deps install after checkout)"

say "repo $REPO_DIR"
if [[ -d "$REPO_DIR/.git" ]]; then
  if runuser -u "$RUN_USER" -- git -C "$REPO_DIR" fetch --quiet origin main \
     && runuser -u "$RUN_USER" -- git -C "$REPO_DIR" reset --quiet --hard origin/main; then
    note "updated to $(runuser -u "$RUN_USER" -- git -C "$REPO_DIR" log --oneline -1)"
  else note "WARNING: origin unreachable, keeping tree as-is"; fi
elif [[ -e "$REPO_DIR" ]]; then echo "$REPO_DIR exists but not a repo — fix manually" >&2; exit 1;
else
  parent="$(dirname "$REPO_DIR")"
  [[ -d "$parent" ]] || install -d -m 755 -o "$RUN_USER" -g "$RUN_USER" "$parent"
  runuser -u "$RUN_USER" -- git clone --quiet "$REPO_URL" "$REPO_DIR"
  note "cloned"
fi
ops_dir="$REPO_DIR/ops"; [[ -f "$ops_dir/magnit.sh" ]] || ops_dir="$src_dir"

say "python deps"
runuser -u "$RUN_USER" -- "$VENV_DIR/bin/pip" install -q -r "$ops_dir/../magnit/requirements.txt" \
  || { echo "pip install failed" >&2; exit 1; }
note "deps installed"
runuser -u "$RUN_USER" -- "$VENV_DIR/bin/python" -c "import pandas,numpy,openpyxl,pypdf,requests; print('imports ok')"

say "wrapper /usr/local/sbin/magnit"
tmp="$(mktemp)"; sed 's/\r$//' "$ops_dir/magnit.sh" > "$tmp"; bash -n "$tmp" \
  || { echo "wrapper broken" >&2; rm -f "$tmp"; exit 1; }
install -m 750 -o root -g "$RUN_USER" "$tmp" /usr/local/sbin/magnit; rm -f "$tmp"
note "installed (750 root:$RUN_USER)"

say "env $ETC_DIR/env"
install -d -m 750 -o root -g "$RUN_USER" "$ETC_DIR"
if [[ -f "$ETC_DIR/env" ]]; then note "exists — NOT touching (secrets)";
  chown root:"$RUN_USER" "$ETC_DIR/env"; chmod 640 "$ETC_DIR/env";
else
  sed 's/\r$//' "$ops_dir/env.example" > "$ETC_DIR/env"
  chown root:"$RUN_USER" "$ETC_DIR/env"; chmod 640 "$ETC_DIR/env"
  note "created from template — FILL TINVEST_TOKEN + CLOUDFLARE_* before first run"
fi

say "units systemd"
changed=0
for unit in "${UNITS[@]}"; do for kind in service timer; do
  src="$ops_dir/$unit.$kind"; dst="/etc/systemd/system/$unit.$kind"
  [[ -f "$src" ]] || { echo "missing $src" >&2; exit 1; }
  tmp="$(mktemp)"; sed 's/\r$//' "$src" > "$tmp"
  if [[ -f "$dst" ]] && cmp -s "$tmp" "$dst"; then note "$unit.$kind unchanged";
  else install -m 644 -o root -g root "$tmp" "$dst"; note "$unit.$kind installed"; changed=1; fi
  rm -f "$tmp"
done; done
if [[ $changed -eq 1 ]]; then systemctl daemon-reload; note "daemon-reload"; fi
systemctl enable --now "${UNITS[@]/%/.timer}" >/dev/null
note "timers enabled"

say "alert bridge"
[[ -x /usr/local/sbin/dash-alert ]] && note "dash-alert present" \
  || note "WARNING: dash-alert missing (839-data) — failures will be silent"

say "selftest"
runuser -u "$RUN_USER" -- /usr/local/sbin/magnit selftest \
  || note "WARNING: selftest found problems (see above)"

say "state"
systemctl list-timers --all 'magnit-*' --no-pager || true
printf '\nDone. Logs: journalctl -u magnit-daily -n 50\n'
printf 'Next: fill %s/env, then: sudo runuser -u %s -- /usr/local/sbin/magnit monthly\n' "$ETC_DIR" "$RUN_USER"
