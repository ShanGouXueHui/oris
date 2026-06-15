#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
SERVICE="$HOME/.config/systemd/user/oris-dev-employee-web-console.service"
LOG_DIR="logs/dev_employee/web_console_public_submit_e2e"
LOG_FILE="$LOG_DIR/finish-public-web-submit-$(date +%Y%m%d%H%M%S).log"
STATUS_FILE="/tmp/oris-public-web-e2e-status-$$.json"
mkdir -p "$LOG_DIR"

TASK_ID="${1:-}"
if [ -z "$TASK_ID" ]; then
  read -p "Task ID submitted from public Web UI: " TASK_ID
fi
if [ -z "$TASK_ID" ]; then
  echo "TASK_ID_REQUIRED"
  exit 1
fi

TOKEN=""
if [ -f "$ENV_FILE" ]; then
  TOKEN="$(awk -F= '/^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=/ {print substr($0, index($0, "=")+1)}' "$ENV_FILE" | tail -n 1)"
fi
if [ -z "$TOKEN" ]; then
  echo "CONSOLE_TOKEN_MISSING"
  exit 1
fi

FINAL_STATUS="unknown"
CANONICAL_STATUS="unknown"
TERMINAL="false"
FAILURE_CODE=""
PRODUCT_COMMIT=""
PRODUCT_REMOTE=""
ORIS_EVIDENCE=""

{
  echo "===== timestamp ====="
  date -Is
  echo
  echo "===== task ====="
  echo "TASK_ID=$TASK_ID"
  echo
  echo "===== persistent public submit policy ====="
  grep 'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED\|ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST' "$SERVICE" || true
  sudo grep -n 'location = /api/goals\|request_method\|127.0.0.1:18892\|127.0.0.1:18893\|auth_basic' /etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf || true
  echo
  echo "===== poll task status ====="
  for i in $(seq 1 120); do
    HTTP_CODE="$(curl -sS -o "$STATUS_FILE" -w '%{http_code}' -H "X-ORIS-Console-Token: $TOKEN" "http://127.0.0.1:18893/api/goals/$TASK_ID" || true)"
    FINAL_STATUS="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
    print(data.get('status', 'unknown'))
except Exception:
    print('unknown')
PY
)"
    CANONICAL_STATUS="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
    print(data.get('canonical_status') or data.get('status') or 'unknown')
except Exception:
    print('unknown')
PY
)"
    TERMINAL="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
    print('true' if data.get('terminal') is True else 'false')
except Exception:
    print('false')
PY
)"
    FAILURE_CODE="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
    print(data.get('failure_code') or '')
except Exception:
    print('')
PY
)"
    if [ "$TERMINAL" != "true" ]; then
      TERMINAL="$(python3 scripts/dev_employee_task_states.py "$FINAL_STATUS" --field terminal 2>/dev/null || echo false)"
      CANONICAL_STATUS="$(python3 scripts/dev_employee_task_states.py "$FINAL_STATUS" --field canonical_status 2>/dev/null || echo "$FINAL_STATUS")"
    fi
    echo "POLL=$i HTTP=$HTTP_CODE STATUS=$FINAL_STATUS CANONICAL=$CANONICAL_STATUS TERMINAL=$TERMINAL"
    if [ "$TERMINAL" = "true" ]; then
      break
    fi
    sleep 10
  done
  echo
  echo "===== final status payload ====="
  python3 -m json.tool "$STATUS_FILE" 2>/dev/null || cat "$STATUS_FILE" || true
  echo
  echo "===== product repo ====="
  if [ -d /home/admin/projects/oris-final-acceptance-api/.git ]; then
    cd /home/admin/projects/oris-final-acceptance-api || exit 1
    git log -1 --oneline || true
    git status --short || true
    git remote -v || true
    cd /home/admin/projects/oris || exit 1
  else
    echo "PRODUCT_REPO_MISSING"
  fi
  echo
  echo "===== public entry remains protected ====="
  echo "UNAUTH_HEALTH_HTTP=$(curl -sS -o /dev/null -w '%{http_code}' https://control.orisfy.com/health || true)"
  echo "UNAUTH_POST_HTTP=$(curl -sS -o /dev/null -w '%{http_code}' -X POST https://control.orisfy.com/api/goals -H 'Content-Type: application/json' -d '{}' || true)"
  echo
  echo "===== services ====="
  echo "WEB_CONSOLE=$(systemctl --user is-active oris-dev-employee-web-console.service 2>/dev/null || true)"
  echo "INTAKE=$(systemctl --user is-active oris-dev-employee-intake.service 2>/dev/null || true)"
  echo "BRIDGE=$(systemctl --user is-active oris-dev-employee-bridge.service 2>/dev/null || true)"
  echo
} | tee "$LOG_FILE"

PRODUCT_COMMIT="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data=json.load(open(sys.argv[1], encoding='utf-8'))
    ev=data.get('github_evidence') or {}
    print(ev.get('product_commit_sha') or data.get('product_commit_sha') or '')
except Exception:
    print('')
PY
)"
PRODUCT_REMOTE="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data=json.load(open(sys.argv[1], encoding='utf-8'))
    ev=data.get('github_evidence') or {}
    print(ev.get('product_remote_sha') or data.get('product_remote_sha') or '')
except Exception:
    print('')
PY
)"
ORIS_EVIDENCE="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data=json.load(open(sys.argv[1], encoding='utf-8'))
    ev=data.get('github_evidence') or {}
    print(ev.get('oris_evidence_commit_sha') or data.get('oris_evidence_commit_sha') or '')
except Exception:
    print('')
PY
)"

git add "$LOG_FILE"
if git diff --cached --quiet; then
  LOG_COMMIT="NO_LOG_CHANGES"
else
  git commit -m "test(dev-employee): finish public web submit e2e"
  git push origin main
  LOG_COMMIT="$(git rev-parse --short HEAD)"
fi

rm -f "$STATUS_FILE"

echo
echo "===== SUMMARY ====="
if [ "$CANONICAL_STATUS" = "completed" ]; then
  SUMMARY_RESULT="PASS"
elif [ "$TERMINAL" = "true" ]; then
  SUMMARY_RESULT="FAILED"
else
  SUMMARY_RESULT="REVIEW"
fi
echo "RESULT=$SUMMARY_RESULT"
echo "TASK_ID=$TASK_ID"
echo "FINAL_STATUS=$FINAL_STATUS"
echo "CANONICAL_STATUS=$CANONICAL_STATUS"
echo "TERMINAL=$TERMINAL"
echo "FAILURE_CODE=$FAILURE_CODE"
echo "PRODUCT_COMMIT_SHA=$PRODUCT_COMMIT"
echo "PRODUCT_REMOTE_SHA=$PRODUCT_REMOTE"
echo "ORIS_EVIDENCE_COMMIT_SHA=$ORIS_EVIDENCE"
echo "LOG_COMMIT=$LOG_COMMIT"
echo "PUBLIC_WEB_SUBMIT_MODE=persistent"
echo "PUBLIC_ENTRY=https://control.orisfy.com"
echo "WEB_CONSOLE_SERVICE=$(systemctl --user is-active oris-dev-employee-web-console.service 2>/dev/null || true)"
echo "INTAKE_SERVICE=$(systemctl --user is-active oris-dev-employee-intake.service 2>/dev/null || true)"
echo "BRIDGE_SERVICE=$(systemctl --user is-active oris-dev-employee-bridge.service 2>/dev/null || true)"
echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
echo "===== END SUMMARY ====="
