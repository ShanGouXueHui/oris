#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

LOG_DIR="logs/dev_employee/nginx_readonly_console_orisfy"
LOG_FILE="$LOG_DIR/control-orisfy-apply-verify-$(date +%Y%m%d%H%M%S).log"
mkdir -p "$LOG_DIR"

echo "This script will apply the read-only Nginx route for control.orisfy.com and verify it."
echo "It will ask for Basic Auth credentials only for verification. The password is not written to the log."
echo
read -p "Basic Auth username: " BA_USER
read -s -p "Basic Auth password: " BA_PASS
echo

{
  echo "===== timestamp ====="
  date -Is
  echo

  echo "===== git sync ====="
  git fetch origin main
  git reset --hard origin/main
  git rev-parse HEAD
  echo

  echo "===== env ====="
  python3 scripts/dev_employee_nginx_readonly_console_from_env.py show
  echo

  echo "===== DNS ====="
  echo "control.orisfy.com:"
  dig +short control.orisfy.com || true
  echo "server public ip:"
  curl -4 -sS ifconfig.me || true
  echo
  echo

  echo "===== required files via sudo ====="
  sudo test -f /etc/nginx/oris-dev-employee.htpasswd && echo "HTPASSWD_OK" || echo "HTPASSWD_MISSING"
  sudo test -f /etc/letsencrypt/live/control.orisfy.com/fullchain.pem && echo "CERT_OK" || echo "CERT_MISSING"
  sudo test -f /etc/letsencrypt/live/control.orisfy.com/privkey.pem && echo "KEY_OK" || echo "KEY_MISSING"
  echo

  echo "===== dry-run ====="
  python3 scripts/dev_employee_nginx_readonly_console_from_env.py dry-run || true
  echo

  echo "===== readiness ====="
  python3 scripts/dev_employee_nginx_readonly_console_from_env.py readiness || true
  echo

  echo "===== apply ====="
  python3 scripts/dev_employee_nginx_readonly_console_from_env.py apply || true
  echo

  echo "===== nginx status ====="
  sudo nginx -t || true
  systemctl is-active nginx || true
  echo

  echo "===== config safety grep ====="
  sudo grep -n '127.0.0.1:18892\|127.0.0.1:18893\|request_method\|auth_basic' /etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf || true
  echo

  echo "===== local submit disabled ====="
  grep ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED "$HOME/.config/systemd/user/oris-dev-employee-web-console.service" || true
  echo

  echo "===== public unauth health should be 401 ====="
  curl -sS -o /tmp/orisfy_unauth.out -w '%{http_code}\n' https://control.orisfy.com/health || true
  cat /tmp/orisfy_unauth.out || true
  echo

  echo "===== public auth health should be 200 ====="
  curl -sS -u "$BA_USER:$BA_PASS" -o /tmp/orisfy_auth_health.out -w '%{http_code}\n' https://control.orisfy.com/health || true
  cat /tmp/orisfy_auth_health.out || true
  echo

  echo "===== public auth POST /api/goals should be 403 ====="
  curl -sS -u "$BA_USER:$BA_PASS" -X POST https://control.orisfy.com/api/goals \
    -H 'Content-Type: application/json' \
    -d '{}' \
    -o /tmp/orisfy_post_goals.out \
    -w '%{http_code}\n' || true
  cat /tmp/orisfy_post_goals.out || true
  echo

  echo "===== final local service checks ====="
  systemctl --user is-active oris-dev-employee-web-console.service || true
  systemctl --user is-active oris-dev-employee-intake.service || true
  systemctl --user is-active oris-dev-employee-bridge.service || true
  echo
} | tee "$LOG_FILE"

unset BA_PASS

git add "$LOG_FILE"
if git diff --cached --quiet; then
  echo "NO_LOG_CHANGES_TO_COMMIT"
else
  git commit -m "test(dev-employee): verify orisfy readonly console apply"
  git push origin main
fi

git log -1 --oneline
