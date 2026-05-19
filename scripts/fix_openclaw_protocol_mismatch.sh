#!/usr/bin/env bash

ROOT_DIR="${ORIS_REPO_DIR:-$HOME/projects/oris}"
BRANCH="${ORIS_BRANCH:-main}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_JSON="logs/dev_employee/latest_openclaw_protocol_fix.json"
LOG_MD="logs/dev_employee/latest_openclaw_protocol_fix.md"
RUN_DIR="run/openclaw_protocol_fix/$TS"

cd "$ROOT_DIR" || exit 1
mkdir -p logs/dev_employee "$RUN_DIR"

OLD_UNIT="$HOME/.config/systemd/user/openclaw-gateway.service"
BACKUP_UNIT="$RUN_DIR/openclaw-gateway.service.before"
cp -a "$OLD_UNIT" "$BACKUP_UNIT" 2>/dev/null || true

cat > "$RUN_DIR/precheck.txt" <<EOF
===== which openclaw =====
$(command -v openclaw || true)

===== which openclaw-gateway =====
$(command -v openclaw-gateway || true)

===== openclaw version =====
$(openclaw --version 2>&1 || true)

===== openclaw gateway status before =====
$(systemctl --user status openclaw-gateway.service --no-pager -l 2>&1 | tail -n 60 || true)

===== old unit =====
$(cat "$OLD_UNIT" 2>/dev/null || true)
EOF

OPENCLAW_BIN="$(command -v openclaw || true)"
if [ -z "$OPENCLAW_BIN" ]; then
  echo "openclaw binary not found" >&2
  exit 2
fi

mkdir -p "$HOME/.config/systemd/user"
cat > "$OLD_UNIT" <<EOF
[Unit]
Description=OpenClaw Gateway (managed by ORIS)
After=network.target

[Service]
Type=simple
ExecStart=$OPENCLAW_BIN gateway --port 18789
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user restart openclaw-gateway.service
sleep 5

STATUS_RC=0
systemctl --user is-active --quiet openclaw-gateway.service || STATUS_RC=$?

cat > "$RUN_DIR/postcheck.txt" <<EOF
===== new unit =====
$(cat "$OLD_UNIT" 2>/dev/null || true)

===== openclaw gateway status after =====
$(systemctl --user status openclaw-gateway.service --no-pager -l 2>&1 | tail -n 80 || true)

===== local gateway head =====
$(curl -I --max-time 5 http://127.0.0.1:18789/ 2>&1 | tail -n 40 || true)

===== public dashboard head =====
$(curl -I --max-time 8 https://control.orisfy.com/ 2>&1 | tail -n 40 || true)

===== recent protocol logs =====
$(journalctl --user -u openclaw-gateway.service -n 80 --no-pager 2>&1 | tail -n 80 || true)
EOF

python3 - <<PY > "$LOG_JSON"
import json
from pathlib import Path
payload = {
  "ok": $([ "$STATUS_RC" -eq 0 ] && echo true || echo false),
  "timestamp_utc": "$TS",
  "openclaw_bin": "$OPENCLAW_BIN",
  "unit_path": "$OLD_UNIT",
  "backup_unit": "$BACKUP_UNIT",
  "status_rc": $STATUS_RC,
  "precheck": Path("$RUN_DIR/precheck.txt").read_text(errors="replace")[-8000:],
  "postcheck": Path("$RUN_DIR/postcheck.txt").read_text(errors="replace")[-12000:]
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY

cat > "$LOG_MD" <<EOF
# OpenClaw Protocol Fix

- timestamp_utc: $TS
- ok: $([ "$STATUS_RC" -eq 0 ] && echo true || echo false)
- openclaw_bin: $OPENCLAW_BIN
- unit_path: $OLD_UNIT
- backup_unit: $BACKUP_UNIT
- status_rc: $STATUS_RC

See JSON: \\`$LOG_JSON\\`
EOF

git add "$LOG_JSON" "$LOG_MD" scripts/fix_openclaw_protocol_mismatch.sh
if ! git diff --cached --quiet; then
  git commit -m "logs(openclaw): record protocol mismatch fix" >/tmp/openclaw_protocol_fix_git.log 2>&1 || true
fi

git pull --rebase origin "$BRANCH" >/tmp/openclaw_protocol_fix_pull.log 2>&1 || true
git push origin "$BRANCH" >/tmp/openclaw_protocol_fix_push.log 2>&1 || true

HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "OPENCLAW_PROTOCOL_FIX_REF=${HEAD_SHORT} ${LOG_JSON} ${LOG_MD}"
exit "$STATUS_RC"
