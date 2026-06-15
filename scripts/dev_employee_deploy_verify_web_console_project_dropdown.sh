#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
LOG_DIR="logs/dev_employee/web_console_project_dropdown"
LOG_FILE="$LOG_DIR/project-dropdown-deploy-$(date +%Y%m%d%H%M%S).log"
API_RESULT="/tmp/oris-project-dropdown-api-$$.json"
mkdir -p "$LOG_DIR"

PATCH_RESULT="unknown"
API_HTTP="000"
PROJECT_FOUND="false"
UI_MARKER_FOUND="false"

{
  echo "===== timestamp ====="
  date -Is
  echo

  echo "===== git sync ====="
  git fetch origin main
  git reset --hard origin/main
  git rev-parse HEAD
  echo

  echo "===== apply project dropdown patch ====="
  if grep -q 'Project list loads automatically after the token changes' scripts/dev_employee_web_console.py; then
    PATCH_RESULT="already_applied"
    echo "PATCH_RESULT=$PATCH_RESULT"
  else
    python3 scripts/dev_employee_patch_web_console_project_dropdown.py
    PATCH_RESULT="applied"
    echo "PATCH_RESULT=$PATCH_RESULT"
  fi
  echo

  echo "===== static checks ====="
  python3 -m py_compile scripts/dev_employee_web_console.py
  grep -n 'Project list loads automatically\|Unable to load projects\|addEventListener' scripts/dev_employee_web_console.py || true
  echo

  echo "===== restart web console ====="
  systemctl --user restart oris-dev-employee-web-console.service
  sleep 2
  systemctl --user is-active oris-dev-employee-web-console.service || true
  echo

  echo "===== local health ====="
  curl -sS -i http://127.0.0.1:18893/health || true
  echo

  echo "===== authenticated local project API ====="
  TOKEN=""
  if [ -f "$ENV_FILE" ]; then
    TOKEN="$(awk -F= '/^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=/ {print substr($0, index($0, "=")+1)}' "$ENV_FILE" | tail -n 1)"
  fi
  if [ -z "$TOKEN" ]; then
    echo "CONSOLE_TOKEN_MISSING"
  else
    API_HTTP="$(curl -sS -o "$API_RESULT" -w '%{http_code}' -H "X-ORIS-Console-Token: $TOKEN" http://127.0.0.1:18893/api/projects || true)"
    echo "API_HTTP=$API_HTTP"
    python3 -m json.tool "$API_RESULT" 2>/dev/null || cat "$API_RESULT" || true
    PROJECT_FOUND="$(python3 - "$API_RESULT" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
    print('true' if 'oris-final-acceptance-api' in (data.get('projects') or []) else 'false')
except Exception:
    print('false')
PY
)"
    echo "PROJECT_FOUND=$PROJECT_FOUND"
  fi
  echo

  echo "===== rendered UI markers ====="
  if curl -sS http://127.0.0.1:18893/ | grep -q 'Project list loads automatically after the token changes'; then
    UI_MARKER_FOUND="true"
  fi
  echo "UI_MARKER_FOUND=$UI_MARKER_FOUND"
  echo

  echo "===== persistent public submit policy remains enabled ====="
  grep 'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED\|ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST' "$HOME/.config/systemd/user/oris-dev-employee-web-console.service" || true
  sudo grep -n 'location = /api/goals\|request_method\|127.0.0.1:18892\|127.0.0.1:18893\|auth_basic' /etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf || true
  echo
} | tee "$LOG_FILE"

rm -f "$API_RESULT"

git add scripts/dev_employee_web_console.py "$LOG_FILE"
if git diff --cached --quiet; then
  LOG_COMMIT="NO_CHANGES"
else
  git commit -m "fix(dev-employee): make project dropdown token-aware"
  git push origin main
  LOG_COMMIT="$(git rev-parse --short HEAD)"
fi

WEB_STATUS="$(systemctl --user is-active oris-dev-employee-web-console.service 2>/dev/null || true)"
RESULT="REVIEW"
if [ "$API_HTTP" = "200" ] && [ "$PROJECT_FOUND" = "true" ] && [ "$UI_MARKER_FOUND" = "true" ] && [ "$WEB_STATUS" = "active" ]; then
  RESULT="PASS"
fi

echo
echo "===== SUMMARY ====="
echo "RESULT=$RESULT"
echo "PATCH_RESULT=$PATCH_RESULT"
echo "GIT_COMMIT=$LOG_COMMIT"
echo "PROJECT_API_HTTP=$API_HTTP"
echo "PROJECT_FOUND=$PROJECT_FOUND"
echo "UI_MARKER_FOUND=$UI_MARKER_FOUND"
echo "WEB_CONSOLE_SERVICE=$WEB_STATUS"
echo "NEXT_ACTION=hard_refresh_browser_then_paste_current_console_token"
echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
echo "===== END SUMMARY ====="
