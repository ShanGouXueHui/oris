#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

LOG_DIR="logs/dev_employee/nginx_readonly_console_orisfy"
LOG_FILE="$LOG_DIR/control-orisfy-conflict-fix-$(date +%Y%m%d%H%M%S).log"
mkdir -p "$LOG_DIR"

echo "This script disables the old sites-enabled/control.orisfy.com.conf entry so the read-only ORIS console config can own control.orisfy.com."
echo "It keeps backups, runs nginx -t, reloads Nginx, and verifies 401/200/403 behavior."
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

  echo "===== before duplicate server_name scan ====="
  sudo grep -RIn "server_name .*control\.orisfy\.com\|control\.orisfy\.com" /etc/nginx/sites-enabled /etc/nginx/conf.d 2>/dev/null || true
  echo

  echo "===== local web console health before fix ====="
  curl -sS -i http://127.0.0.1:18893/health || true
  echo

  echo "===== disable old sites-enabled entry if present ====="
  TS="$(date +%Y%m%d%H%M%S)"
  if [ -e /etc/nginx/sites-enabled/control.orisfy.com.conf ] || [ -L /etc/nginx/sites-enabled/control.orisfy.com.conf ]; then
    sudo mv /etc/nginx/sites-enabled/control.orisfy.com.conf "/etc/nginx/sites-enabled/control.orisfy.com.conf.disabled_${TS}"
    echo "DISABLED_OLD_SITES_ENABLED=/etc/nginx/sites-enabled/control.orisfy.com.conf.disabled_${TS}"
  else
    echo "NO_OLD_SITES_ENABLED_ENTRY"
  fi
  echo

  echo "===== nginx syntax and reload ====="
  sudo nginx -t || true
  sudo systemctl reload nginx || true
  systemctl is-active nginx || true
  echo

  echo "===== after duplicate server_name scan ====="
  sudo grep -RIn "server_name .*control\.orisfy\.com\|control\.orisfy\.com" /etc/nginx/sites-enabled /etc/nginx/conf.d 2>/dev/null || true
  echo

  echo "===== effective readonly config safety grep ====="
  sudo grep -n '127.0.0.1:18892\|127.0.0.1:18893\|request_method\|auth_basic\|server_name control.orisfy.com' /etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf || true
  echo

  echo "===== public unauth health should be 401 ====="
  curl -sS -o /tmp/orisfy_unauth_after_fix.out -w '%{http_code}\n' https://control.orisfy.com/health || true
  cat /tmp/orisfy_unauth_after_fix.out || true
  echo

  echo "===== public auth health should be 200 ====="
  curl -sS -u "$BA_USER:$BA_PASS" -o /tmp/orisfy_auth_health_after_fix.out -w '%{http_code}\n' https://control.orisfy.com/health || true
  cat /tmp/orisfy_auth_health_after_fix.out || true
  echo

  echo "===== public auth POST /api/goals should be 403 ====="
  curl -sS -u "$BA_USER:$BA_PASS" -X POST https://control.orisfy.com/api/goals \
    -H 'Content-Type: application/json' \
    -d '{}' \
    -o /tmp/orisfy_post_goals_after_fix.out \
    -w '%{http_code}\n' || true
  cat /tmp/orisfy_post_goals_after_fix.out || true
  echo

  echo "===== local submit disabled ====="
  grep ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED "$HOME/.config/systemd/user/oris-dev-employee-web-console.service" || true
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
  git commit -m "test(dev-employee): verify orisfy console nginx conflict fix"
  git push origin main
fi

git log -1 --oneline
