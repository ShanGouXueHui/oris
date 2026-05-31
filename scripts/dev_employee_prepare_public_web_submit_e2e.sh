#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

SERVICE="$HOME/.config/systemd/user/oris-dev-employee-web-console.service"
ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
NGINX_CONF="/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf"
LOG_DIR="logs/dev_employee/web_console_public_submit_e2e"
LOG_FILE="$LOG_DIR/prepare-public-web-submit-$(date +%Y%m%d%H%M%S).log"
mkdir -p "$LOG_DIR"

{
  echo "===== timestamp ====="
  date -Is
  echo

  echo "===== git sync ====="
  git fetch origin main
  git reset --hard origin/main
  git rev-parse HEAD
  echo

  echo "===== current public route safety before temporary window ====="
  curl -sS -o /tmp/orisfy_public_post_before.out -w '%{http_code}\n' -X POST https://control.orisfy.com/api/goals -H 'Content-Type: application/json' -d '{}' || true
  cat /tmp/orisfy_public_post_before.out || true
  echo

  echo "===== nginx config before ====="
  sudo grep -n 'location = /api/goals\|request_method\|proxy_pass http://127.0.0.1:18893\|127.0.0.1:18892\|auth_basic' "$NGINX_CONF" || true
  echo

  echo "===== web console service before ====="
  grep 'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED\|ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST' "$SERVICE" || true
  echo

  echo "===== open temporary public submit window ====="
  TS="$(date +%Y%m%d%H%M%S)"
  sudo cp "$NGINX_CONF" "${NGINX_CONF}.bak_public_submit_${TS}"
  echo "NGINX_BACKUP=${NGINX_CONF}.bak_public_submit_${TS}"
  sudo python3 - <<'PY'
from pathlib import Path
p = Path('/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf')
text = p.read_text(encoding='utf-8')
old = 'location = /api/goals {\n        if ($request_method !~ ^(GET)$) { return 403; }'
new = 'location = /api/goals {\n        if ($request_method !~ ^(GET|POST)$) { return 403; }'
if old not in text:
    raise SystemExit('expected exact /api/goals read-only guard not found')
p.write_text(text.replace(old, new, 1), encoding='utf-8')
PY
  python3 - <<'PY'
from pathlib import Path
import re
from datetime import datetime
svc = Path.home() / '.config' / 'systemd' / 'user' / 'oris-dev-employee-web-console.service'
text = svc.read_text(encoding='utf-8')
backup = svc.with_suffix(svc.suffix + f'.bak_public_submit_{datetime.now().strftime("%Y%m%d%H%M%S")}')
backup.write_text(text, encoding='utf-8')
pattern = r'^Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=.*$'
if re.search(pattern, text, flags=re.MULTILINE):
    text = re.sub(pattern, 'Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=1', text, flags=re.MULTILINE)
else:
    text = text.replace('[Service]\n', '[Service]\nEnvironment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=1\n', 1)
svc.write_text(text, encoding='utf-8')
print(f'SERVICE_BACKUP={backup}')
PY
  sudo nginx -t
  sudo systemctl reload nginx
  systemctl --user daemon-reload
  systemctl --user restart oris-dev-employee-web-console.service
  sleep 2
  echo

  echo "===== nginx config after temporary window ====="
  sudo grep -n 'location = /api/goals\|request_method\|proxy_pass http://127.0.0.1:18893\|127.0.0.1:18892\|auth_basic' "$NGINX_CONF" || true
  echo

  echo "===== web console service after ====="
  grep 'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED\|ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST' "$SERVICE" || true
  echo

  echo "===== public health should still require Basic Auth ====="
  curl -sS -o /tmp/orisfy_public_health_noauth_prepare.out -w '%{http_code}\n' https://control.orisfy.com/health || true
  cat /tmp/orisfy_public_health_noauth_prepare.out || true
  echo

  echo "===== local services after ====="
  systemctl --user is-active oris-dev-employee-web-console.service || true
  systemctl --user is-active oris-dev-employee-intake.service || true
  systemctl --user is-active oris-dev-employee-bridge.service || true
  echo

  echo "===== token presence only; token not logged ====="
  if [ -f "$ENV_FILE" ]; then
    grep -q '^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=' "$ENV_FILE" && echo "CONSOLE_TOKEN_PRESENT" || echo "CONSOLE_TOKEN_MISSING"
  else
    echo "ENV_FILE_MISSING=$ENV_FILE"
  fi
  echo
} | tee "$LOG_FILE"

git add "$LOG_FILE"
if git diff --cached --quiet; then
  echo "NO_LOG_CHANGES_TO_COMMIT"
else
  git commit -m "test(dev-employee): prepare public web submit e2e"
  git push origin main
fi

echo
echo "===== CONSOLE TOKEN - NOT LOGGED TO GITHUB ====="
TOKEN=""
if [ -f "$ENV_FILE" ]; then
  TOKEN="$(awk -F= '/^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=/ {print substr($0, index($0, "=")+1)}' "$ENV_FILE" | tail -n 1)"
fi
if [ -n "$TOKEN" ]; then
  echo "$TOKEN"
else
  echo "TOKEN_NOT_FOUND_IN_$ENV_FILE"
fi

echo
echo "===== PUBLIC WEB UI E2E ====="
echo "Open: https://control.orisfy.com"
echo "Use Basic Auth first, then paste the Console Token above into the Web UI token field."
echo "Project: oris-final-acceptance-api"
echo "Task ID: public-web-ui-real-e2e-readonly-e2e-$(date +%Y%m%d%H%M%S)"
echo "Objective: Add a minimal FastAPI GET /readonly-e2e endpoint that returns exactly {\"readonly_e2e\": true}, add pytest coverage for status code and exact JSON, run tests, commit and push."
echo "Expected checks: pytest"
echo "Commit message: feat(api): add readonly e2e endpoint"
echo
echo "After submitting in the public Web UI, run scripts/dev_employee_finish_public_web_submit_e2e.sh and paste the task id when prompted."
echo
git log -1 --oneline
