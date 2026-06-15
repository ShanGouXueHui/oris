#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
LOG_DIR="logs/dev_employee/web_console_external_js"
LOG_FILE="$LOG_DIR/external-js-deploy-$(date +%Y%m%d%H%M%S).log"
APP_JS_FILE="/tmp/oris-web-console-app-$$.js"
APP_JS_HEADERS="/tmp/oris-web-console-app-$$.headers"
PROJECT_FILE="/tmp/oris-web-console-projects-$$.json"
mkdir -p "$LOG_DIR"

PATCH_RESULT="unknown"
JS_HTTP="000"
JS_CONTENT_TYPE="missing"
JS_SYNTAX="not_checked"
HTML_EXTERNAL_SCRIPT="false"
HTML_INLINE_ONCLICK="true"
PROJECT_API_HTTP="000"
PROJECT_FOUND="false"
PUBLIC_HEALTH_HTTP="000"

{
  echo "===== timestamp ====="
  date -Is
  echo

  echo "===== git sync ====="
  git fetch origin main
  git reset --hard origin/main
  git rev-parse HEAD
  echo

  echo "===== externalize JavaScript ====="
  if grep -q '<script src="/app.js" defer></script>' scripts/dev_employee_web_console.py; then
    PATCH_RESULT="already_applied"
    echo "PATCH_RESULT=$PATCH_RESULT"
  else
    python3 scripts/dev_employee_externalize_web_console_js.py
    PATCH_RESULT="applied"
    echo "PATCH_RESULT=$PATCH_RESULT"
  fi
  echo

  echo "===== Python static check ====="
  python3 -m py_compile scripts/dev_employee_web_console.py
  echo "PY_COMPILE=PASS"
  echo

  echo "===== restart Web Console ====="
  systemctl --user restart oris-dev-employee-web-console.service
  sleep 2
  systemctl --user is-active oris-dev-employee-web-console.service || true
  echo

  echo "===== rendered HTML check ====="
  HTML="$(curl -sS http://127.0.0.1:18893/ || true)"
  if printf '%s' "$HTML" | grep -q '<script src="/app.js" defer></script>'; then
    HTML_EXTERNAL_SCRIPT="true"
  fi
  if printf '%s' "$HTML" | grep -q 'onclick='; then
    HTML_INLINE_ONCLICK="true"
  else
    HTML_INLINE_ONCLICK="false"
  fi
  echo "HTML_EXTERNAL_SCRIPT=$HTML_EXTERNAL_SCRIPT"
  echo "HTML_INLINE_ONCLICK=$HTML_INLINE_ONCLICK"
  echo

  echo "===== app.js response ====="
  JS_HTTP="$(curl -sS -D "$APP_JS_HEADERS" -o "$APP_JS_FILE" -w '%{http_code}' http://127.0.0.1:18893/app.js || true)"
  JS_CONTENT_TYPE="$(awk 'BEGIN{IGNORECASE=1} /^Content-Type:/ {sub(/\r$/, ""); print substr($0, index($0, ":")+2); exit}' "$APP_JS_HEADERS")"
  echo "JS_HTTP=$JS_HTTP"
  echo "JS_CONTENT_TYPE=$JS_CONTENT_TYPE"
  grep -n "reload_projects_button.*addEventListener\|submit_goal_button.*addEventListener\|load_status_button.*addEventListener" "$APP_JS_FILE" || true
  echo

  echo "===== JavaScript syntax check ====="
  if command -v node >/dev/null 2>&1; then
    if node --check "$APP_JS_FILE"; then
      JS_SYNTAX="pass"
    else
      JS_SYNTAX="fail"
    fi
  elif command -v nodejs >/dev/null 2>&1; then
    if nodejs --check "$APP_JS_FILE"; then
      JS_SYNTAX="pass"
    else
      JS_SYNTAX="fail"
    fi
  else
    JS_SYNTAX="node_unavailable"
  fi
  echo "JS_SYNTAX=$JS_SYNTAX"
  echo

  echo "===== authenticated project API ====="
  TOKEN=""
  if [ -f "$ENV_FILE" ]; then
    TOKEN="$(awk -F= '/^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=/ {print substr($0, index($0, "=")+1)}' "$ENV_FILE" | tail -n 1)"
  fi
  if [ -z "$TOKEN" ]; then
    echo "CONSOLE_TOKEN_MISSING"
  else
    PROJECT_API_HTTP="$(curl -sS -o "$PROJECT_FILE" -w '%{http_code}' -H "X-ORIS-Console-Token: $TOKEN" http://127.0.0.1:18893/api/projects || true)"
    PROJECT_FOUND="$(python3 - "$PROJECT_FILE" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
    print('true' if 'oris-final-acceptance-api' in (data.get('projects') or []) else 'false')
except Exception:
    print('false')
PY
)"
    echo "PROJECT_API_HTTP=$PROJECT_API_HTTP"
    echo "PROJECT_FOUND=$PROJECT_FOUND"
  fi
  echo

  echo "===== public protection remains enabled ====="
  PUBLIC_HEALTH_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' https://control.orisfy.com/health || true)"
  echo "PUBLIC_UNAUTH_HEALTH_HTTP=$PUBLIC_HEALTH_HTTP"
  grep 'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED\|ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST' "$HOME/.config/systemd/user/oris-dev-employee-web-console.service" || true
  sudo grep -n 'location = /api/goals\|request_method\|127.0.0.1:18892\|127.0.0.1:18893\|auth_basic\|Content-Security-Policy' /etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf || true
  echo
} > >(tee "$LOG_FILE") 2>&1
wait

rm -f "$APP_JS_FILE" "$APP_JS_HEADERS" "$PROJECT_FILE"

git add scripts/dev_employee_web_console.py "$LOG_FILE"
if git diff --cached --quiet; then
  LOG_COMMIT="NO_CHANGES"
else
  git commit -m "fix(dev-employee): serve Web console JavaScript externally"
  git push origin main
  LOG_COMMIT="$(git rev-parse --short HEAD)"
fi

WEB_STATUS="$(systemctl --user is-active oris-dev-employee-web-console.service 2>/dev/null || true)"
RESULT="REVIEW"
if [ "$JS_HTTP" = "200" ] && [ "$HTML_EXTERNAL_SCRIPT" = "true" ] && [ "$HTML_INLINE_ONCLICK" = "false" ] && [ "$PROJECT_API_HTTP" = "200" ] && [ "$PROJECT_FOUND" = "true" ] && [ "$WEB_STATUS" = "active" ]; then
  if [ "$JS_SYNTAX" = "pass" ] || [ "$JS_SYNTAX" = "node_unavailable" ]; then
    RESULT="PASS"
  fi
fi

echo
echo "===== SUMMARY ====="
echo "RESULT=$RESULT"
echo "PATCH_RESULT=$PATCH_RESULT"
echo "GIT_COMMIT=$LOG_COMMIT"
echo "JS_HTTP=$JS_HTTP"
echo "JS_CONTENT_TYPE=$JS_CONTENT_TYPE"
echo "JS_SYNTAX=$JS_SYNTAX"
echo "HTML_EXTERNAL_SCRIPT=$HTML_EXTERNAL_SCRIPT"
echo "HTML_INLINE_ONCLICK=$HTML_INLINE_ONCLICK"
echo "PROJECT_API_HTTP=$PROJECT_API_HTTP"
echo "PROJECT_FOUND=$PROJECT_FOUND"
echo "PUBLIC_UNAUTH_HEALTH_HTTP=$PUBLIC_HEALTH_HTTP"
echo "WEB_CONSOLE_SERVICE=$WEB_STATUS"
echo "NEXT_ACTION=hard_refresh_browser_then_paste_current_console_token_and_click_reload_projects"
echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
echo "===== END SUMMARY ====="
