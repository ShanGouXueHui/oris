#!/usr/bin/env bash

ROOT_DIR="${ORIS_REPO_DIR:-$HOME/projects/oris}"
BRANCH="${ORIS_BRANCH:-main}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="/tmp/oris_openclaw_upgrade_$TS"
LOG_JSON="logs/dev_employee/latest_openclaw_upgrade.json"
LOG_MD="logs/dev_employee/latest_openclaw_upgrade.md"
RUN_LOG="$BACKUP_DIR/upgrade.log"

cd "$ROOT_DIR" || exit 1
mkdir -p "$BACKUP_DIR" logs/dev_employee

{
  echo "===== timestamp ====="
  echo "$TS"

  echo
  echo "===== backup config and units ====="
  cp -a "$HOME/.openclaw/openclaw.json" "$BACKUP_DIR/openclaw.json.before" 2>/dev/null || true
  cp -a "$HOME/.openclaw/secrets.json" "$BACKUP_DIR/secrets.json.before" 2>/dev/null || true
  cp -a "$HOME/.config/systemd/user/openclaw-gateway.service" "$BACKUP_DIR/openclaw-gateway.service.before" 2>/dev/null || true
  cp -a "$HOME/.config/systemd/user/oris-free-mesh-api.service" "$BACKUP_DIR/oris-free-mesh-api.service.before" 2>/dev/null || true

  echo
  echo "===== before versions ====="
  command -v openclaw || true
  openclaw --version 2>&1 || true
  npm list -g --depth=0 2>/dev/null | grep -i openclaw || true

  echo
  echo "===== stop gateway before upgrade ====="
  systemctl --user stop openclaw-gateway.service 2>&1 || true

  echo
  echo "===== npm upgrade openclaw ====="
  npm install -g openclaw@latest 2>&1
  UPGRADE_RC=$?
  echo "UPGRADE_RC=$UPGRADE_RC"

  echo
  echo "===== after versions ====="
  command -v openclaw || true
  openclaw --version 2>&1 || true
  npm list -g --depth=0 2>/dev/null | grep -i openclaw || true

  echo
  echo "===== ensure schema-safe ORIS Free Mesh model patch ====="
  python3 scripts/patch_openclaw_free_mesh_model.py --apply 2>&1 || true

  echo
  echo "===== restart services ====="
  systemctl --user daemon-reload 2>&1 || true
  systemctl --user restart oris-free-mesh-api.service 2>&1 || true
  systemctl --user restart openclaw-gateway.service 2>&1 || true
  sleep 5

  echo
  echo "===== service status ====="
  systemctl --user status oris-free-mesh-api.service --no-pager -l 2>&1 | tail -n 50 || true
  systemctl --user status openclaw-gateway.service --no-pager -l 2>&1 | tail -n 80 || true

  echo
  echo "===== probes ====="
  curl -sS --max-time 5 http://127.0.0.1:8789/v1/health 2>&1 || true
  echo
  curl -I --max-time 5 http://127.0.0.1:18789/ 2>&1 | tail -n 40 || true
  echo
  curl -I --max-time 8 https://control.orisfy.com/ 2>&1 | tail -n 40 || true

  echo
  echo "===== openclaw inspect ====="
  python3 scripts/inspect_openclaw_model_config.py 2>&1 || true

  echo
  echo "===== openclaw dashboard command ====="
  openclaw dashboard 2>&1 | tail -n 120 || true

  echo
  echo "===== recent gateway logs ====="
  journalctl --user -u openclaw-gateway.service -n 160 --no-pager 2>&1 || true
} | tee "$RUN_LOG"

python3 - <<PY > "$LOG_JSON"
import json
from pathlib import Path
run_log = Path("$RUN_LOG").read_text(errors="replace")[-30000:]
payload = {
  "ok": True,
  "timestamp_utc": "$TS",
  "backup_dir": "$BACKUP_DIR",
  "run_log_tail": run_log,
  "expected": {
    "gateway": "active",
    "free_mesh_api": "active",
    "openclaw_primary_model": "openrouter/auto",
    "dashboard_public_head": "401 Basic Auth or 200 after auth"
  }
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY

cat > "$LOG_MD" <<EOF
# OpenClaw Stack Upgrade

- timestamp_utc: $TS
- backup_dir: $BACKUP_DIR
- json: \\`$LOG_JSON\\`
EOF

git add "$LOG_JSON" "$LOG_MD" scripts/upgrade_openclaw_stack.sh scripts/patch_openclaw_free_mesh_model.py scripts/inspect_openclaw_model_config.py
if ! git diff --cached --quiet; then
  git commit -m "logs(openclaw): record stack upgrade" >/tmp/oris_openclaw_upgrade_git.log 2>&1 || true
fi

git pull --rebase origin "$BRANCH" >/tmp/oris_openclaw_upgrade_pull.log 2>&1 || true
git push origin "$BRANCH" >/tmp/oris_openclaw_upgrade_push.log 2>&1 || true

HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "OPENCLAW_UPGRADE_REF=${HEAD_SHORT} ${LOG_JSON} ${LOG_MD}"
