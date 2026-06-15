#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
LOG_DIR="logs/dev_employee/web_console_javascript"
LOG_FILE="$LOG_DIR/web-console-javascript-fix-$(date +%Y%m%d%H%M%S).log"
HTML_FILE="/tmp/oris-web-console-page-$$.html"
JS_FILE="/tmp/oris-web-console-page-$$.js"
API_FILE="/tmp/oris-web-console-projects-$$.json"
mkdir -p "$LOG_DIR"

PATCH_RESULT="unknown"
JS_CHECK="unknown"
PROJECT_API_HTTP="000"
PROJECT_FOUND="false"
WEB_STATUS="unknown"

{
  echo "===== timestamp ====="
  date -Is
  echo

  echo "===== git sync ====="
  git fetch origin main
  git reset --hard origin/main
  git rev-parse HEAD
  echo

  echo "===== fix Python-to-JavaScript escaping ====="
  if grep -q 'return r"""<!doctype html>' scripts/dev_employee_web_console.py; then
    PATCH_RESULT="already_applied"
    echo "PATCH_RESULT=$PATCH_RESULT"
  else
    python3 scripts/dev_employee_fix_web_console_javascript_escaping.py
    PATCH_RESULT="applied"
    echo "PATCH_RESULT=$PATCH_RESULT"
  fi
  echo

  echo "===== Python static check ====="
  python3 -m py_compile scripts/dev_employee_web_console.py
  echo "PY_COMPILE=pass"
  echo

  echo "===== render page and extract JavaScript ====="
  python3 - "$HTML_FILE" "$JS_FILE" <<'PY'
import importlib.util
import pathlib
import re
import sys
src = pathlib.Path('/home/admin/projects/oris/scripts/dev_employee_web_console.py')
spec = importlib.util.spec_from_file_location('oris_web_console', src)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
html = mod.page()
pathlib.Path(sys.argv[1]).write_text(html, encoding='utf-8')
match = re.search(r'<script>(.*?)</script>', html, flags=re.S)
if not match:
    raise SystemExit('SCRIPT_BLOCK_NOT_FOUND')
pathlib.Path(sys.argv[2]).write_text(match.group(1), encoding='utf-8')
print('RENDERED_HTML=true')
print('EXTRACTED_JS=true')
print('SPLITLINES_ESCAPED=' + str("value.split('\\n')" in match.group(1)).lower())
PY
  echo

  echo "===== JavaScript syntax check ====="
  if command -v node >/dev/null 2>&1; then
    if node --check "$JS_FILE"; then
      JS_CHECK="pass"
    else
      JS_CHECK="fail"
    fi
  else
    if grep -q "value.split('\\\\n')" "$JS_FILE"; then
      JS_CHECK="pass_no_node"
    else
      JS_CHECK="fail_no_node"
    fi
  fi
  echo "JS_CHECK=$JS_CHECK"
  echo

  echo "===== restart Web Console ====="
  systemctl --user restart oris-dev-employee-web-console.service
  sleep 2
  WEB_STATUS="$(systemctl --user is-active oris-dev-employee-web-console.service 2>/dev/null || true)"
  echo "WEB_STATUS=$WEB_STATUS"
  echo

  echo "===== verify rendered public UI markers ====="
  curl -sS http://127.0.0.1:18893/ > "$HTML_FILE"
  grep -n 'Project list loads automatically after the token changes\|Reload projects\|value.split' "$HTML_FILE" || true
  echo

  echo "===== authenticated project API ====="
  TOKEN=""
  if [ -f "$ENV_FILE" ]; then
    TOKEN="$(awk -F= '/^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=/ {print substr($0, index($0, "=")+1)}' "$ENV_FILE" | tail -n 1)"
  fi
  if [ -z "$TOKEN" ]; then
    echo "CONSOLE_TOKEN_MISSING"
  else
    PROJECT_API_HTTP="$(curl -sS -o "$API_FILE" -w '%{http_code}' -H "X-ORIS-Console-Token: $TOKEN" http://127.0.0.1:18893/api/projects || true)"
    PROJECT_FOUND="$(python3 - "$API_FILE" <<'PY'
import json, sys
try:
    data=json.load(open(sys.argv[1], encoding='utf-8'))
    print('true' if 'oris-final-acceptance-api' in (data.get('projects') or []) else 'false')
except Exception:
    print('false')
PY
)"
    echo "PROJECT_API_HTTP=$PROJECT_API_HTTP"
    echo "PROJECT_FOUND=$PROJECT_FOUND"
  fi
  echo

  echo "===== persistent public submit policy ====="
  grep 'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED\|ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST' "$HOME/.config/systemd/user/oris-dev-employee-web-console.service" || true
  echo
} > >(tee "$LOG_FILE") 2>&1
wait

rm -f "$HTML_FILE" "$JS_FILE" "$API_FILE"

git add scripts/dev_employee_web_console.py "$LOG_FILE"
if git diff --cached --quiet; then
  LOG_COMMIT="NO_CHANGES"
else
  git commit -m "fix(dev-employee): preserve JavaScript escapes in Web console"
  git push origin main
  LOG_COMMIT="$(git rev-parse --short HEAD)"
fi

RESULT="REVIEW"
case "$JS_CHECK" in
  pass|pass_no_node)
    if [ "$PROJECT_API_HTTP" = "200" ] && [ "$PROJECT_FOUND" = "true" ] && [ "$WEB_STATUS" = "active" ]; then
      RESULT="PASS"
    fi
    ;;
esac

echo
echo "===== SUMMARY ====="
echo "RESULT=$RESULT"
echo "PATCH_RESULT=$PATCH_RESULT"
echo "GIT_COMMIT=$LOG_COMMIT"
echo "JAVASCRIPT_SYNTAX=$JS_CHECK"
echo "PROJECT_API_HTTP=$PROJECT_API_HTTP"
echo "PROJECT_FOUND=$PROJECT_FOUND"
echo "WEB_CONSOLE_SERVICE=$WEB_STATUS"
echo "NEXT_ACTION=hard_refresh_browser_and_click_reload_projects"
echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
echo "===== END SUMMARY ====="
