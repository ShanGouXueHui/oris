#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

SERVICE="$HOME/.config/systemd/user/oris-dev-employee-web-console.service"
ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
LOG_DIR="logs/dev_employee/web_console_local_submit_e2e"
LOG_FILE="$LOG_DIR/prepare-local-web-submit-$(date +%Y%m%d%H%M%S).log"
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

  echo "===== safety: public route must remain read-only ====="
  sudo grep -n 'server_name control.orisfy.com\|127.0.0.1:18892\|127.0.0.1:18893\|request_method\|auth_basic' /etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf || true
  echo

  echo "===== local services before ====="
  systemctl --user is-active oris-dev-employee-web-console.service || true
  systemctl --user is-active oris-dev-employee-intake.service || true
  systemctl --user is-active oris-dev-employee-bridge.service || true
  echo

  echo "===== web console service file before ====="
  grep 'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED\|ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST' "$SERVICE" || true
  echo

  echo "===== enable local-only web submit ====="
  python3 - <<'PY'
from pathlib import Path
import re
from datetime import datetime
svc = Path.home() / ".config" / "systemd" / "user" / "oris-dev-employee-web-console.service"
text = svc.read_text(encoding="utf-8")
backup = svc.with_suffix(svc.suffix + f".bak_{datetime.now().strftime('%Y%m%d%H%M%S')}")
backup.write_text(text, encoding="utf-8")
pattern = r"^Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=.*$"
if re.search(pattern, text, flags=re.MULTILINE):
    text = re.sub(pattern, "Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=1", text, flags=re.MULTILINE)
else:
    text = text.replace("[Service]\n", "[Service]\nEnvironment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=1\n", 1)
svc.write_text(text, encoding="utf-8")
print(f"BACKUP={backup}")
PY
  systemctl --user daemon-reload
  systemctl --user restart oris-dev-employee-web-console.service
  sleep 2
  echo

  echo "===== web console service file after ====="
  grep 'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED\|ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST' "$SERVICE" || true
  echo

  echo "===== local web console health ====="
  curl -sS -i http://127.0.0.1:18893/health || true
  echo

  echo "===== local project allowlist through web console requires token; token not logged ====="
  if [ -f "$ENV_FILE" ]; then
    echo "ENV_FILE_EXISTS=$ENV_FILE"
    grep -q '^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=' "$ENV_FILE" && echo "CONSOLE_TOKEN_PRESENT" || echo "CONSOLE_TOKEN_MISSING"
  else
    echo "ENV_FILE_MISSING=$ENV_FILE"
  fi
  echo

  echo "===== local services after ====="
  systemctl --user is-active oris-dev-employee-web-console.service || true
  systemctl --user is-active oris-dev-employee-intake.service || true
  systemctl --user is-active oris-dev-employee-bridge.service || true
  echo
} | tee "$LOG_FILE"

git add "$LOG_FILE"
if git diff --cached --quiet; then
  echo "NO_LOG_CHANGES_TO_COMMIT"
else
  git commit -m "test(dev-employee): prepare local web submit e2e"
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
echo "===== OPEN WEB UI THROUGH SSH TUNNEL ====="
echo "From your local computer, run:"
echo "ssh -L 18893:127.0.0.1:18893 admin@43.106.55.255"
echo "Then open: http://127.0.0.1:18893"
echo
echo "Recommended UI test values:"
echo "Project: oris-final-acceptance-api"
echo "Task ID: web-ui-real-e2e-readonly-e2e-$(date +%Y%m%d%H%M%S)"
echo "Objective: Add a minimal FastAPI GET /readonly-e2e endpoint that returns exactly {\"readonly_e2e\": true}, add pytest coverage for status code and exact JSON, run tests, commit and push."
echo "Expected checks: pytest"
echo "Commit message: feat(api): add readonly e2e endpoint"
echo
echo "After submitting in the web UI, run scripts/dev_employee_finish_local_web_submit_e2e.sh and paste the task id when prompted."
echo
git log -1 --oneline
