#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

SERVICE="$HOME/.config/systemd/user/oris-dev-employee-web-console.service"
LOG_DIR="logs/dev_employee/web_console_local_submit_e2e"
LOG_FILE="$LOG_DIR/finish-local-web-submit-$(date +%Y%m%d%H%M%S).log"
mkdir -p "$LOG_DIR"

read -p "Task ID submitted from web UI: " TASK_ID
if [ -z "$TASK_ID" ]; then
  echo "TASK_ID_REQUIRED"
  exit 1
fi

{
  echo "===== timestamp ====="
  date -Is
  echo

  echo "===== git sync ====="
  git fetch origin main
  git reset --hard origin/main
  git rev-parse HEAD
  echo

  echo "===== submitted task id ====="
  echo "$TASK_ID"
  echo

  echo "===== poll status through local Web Console API ====="
  TOKEN=""
  ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
  if [ -f "$ENV_FILE" ]; then
    TOKEN="$(awk -F= '/^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=/ {print substr($0, index($0, "=")+1)}' "$ENV_FILE" | tail -n 1)"
  fi
  if [ -z "$TOKEN" ]; then
    echo "CONSOLE_TOKEN_MISSING"
  else
    for i in $(seq 1 90); do
      echo "--- poll $i ---"
      curl -sS -H "X-ORIS-Console-Token: $TOKEN" "http://127.0.0.1:18893/api/goals/$TASK_ID" | python3 -m json.tool || true
      STATUS="$(curl -sS -H "X-ORIS-Console-Token: $TOKEN" "http://127.0.0.1:18893/api/goals/$TASK_ID" | python3 - <<'PY'
import json, sys
try:
    data=json.load(sys.stdin)
    print(data.get('status',''))
except Exception:
    print('')
PY
)"
      echo "STATUS=$STATUS"
      if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] || [ "$STATUS" = "error" ]; then
        break
      fi
      sleep 10
    done
  fi
  echo

  echo "===== final local status via status script if available ====="
  if [ -f scripts/dev_employee_task_status.py ]; then
    python3 scripts/dev_employee_task_status.py "$TASK_ID" || true
  else
    echo "NO_STATUS_SCRIPT"
  fi
  echo

  echo "===== product repo evidence quick check ====="
  if [ -d /home/admin/projects/oris-final-acceptance-api/.git ]; then
    cd /home/admin/projects/oris-final-acceptance-api && git log -1 --oneline && git status --short && git remote -v && cd /home/admin/projects/oris
  else
    echo "PRODUCT_REPO_MISSING=/home/admin/projects/oris-final-acceptance-api"
  fi
  echo

  echo "===== disable local web submit after e2e ====="
  python3 - <<'PY'
from pathlib import Path
import re
svc = Path.home() / ".config" / "systemd" / "user" / "oris-dev-employee-web-console.service"
text = svc.read_text(encoding="utf-8")
text = re.sub(r"^Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=.*$", "Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=0", text, flags=re.MULTILINE)
svc.write_text(text, encoding="utf-8")
PY
  systemctl --user daemon-reload
  systemctl --user restart oris-dev-employee-web-console.service
  sleep 2
  grep ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED "$SERVICE" || true
  echo

  echo "===== verify public route still read-only ====="
  curl -sS -o /tmp/orisfy_public_post_after_web_e2e.out -w '%{http_code}\n' -X POST https://control.orisfy.com/api/goals -H 'Content-Type: application/json' -d '{}' || true
  cat /tmp/orisfy_public_post_after_web_e2e.out || true
  echo

  echo "===== final local service checks ====="
  systemctl --user is-active oris-dev-employee-web-console.service || true
  systemctl --user is-active oris-dev-employee-intake.service || true
  systemctl --user is-active oris-dev-employee-bridge.service || true
  echo
} | tee "$LOG_FILE"

git add "$LOG_FILE"
if git diff --cached --quiet; then
  echo "NO_LOG_CHANGES_TO_COMMIT"
else
  git commit -m "test(dev-employee): finish local web submit e2e"
  git push origin main
fi

git log -1 --oneline
