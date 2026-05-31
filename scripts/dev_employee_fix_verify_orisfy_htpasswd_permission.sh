#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

LOG_DIR="logs/dev_employee/nginx_readonly_console_orisfy"
LOG_FILE="$LOG_DIR/control-orisfy-htpasswd-permission-fix-$(date +%Y%m%d%H%M%S).log"
mkdir -p "$LOG_DIR"

echo "This script fixes Nginx Basic Auth htpasswd readability for control.orisfy.com and verifies 401/200/403 behavior."
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

  echo "===== nginx worker user ====="
  sudo awk '/^user[[:space:]]+/ {print $0}' /etc/nginx/nginx.conf || true
  NGINX_USER="$(sudo awk '/^user[[:space:]]+/ {gsub(";", "", $2); print $2; exit}' /etc/nginx/nginx.conf)"
  if [ -z "$NGINX_USER" ]; then
    NGINX_USER="www-data"
  fi
  echo "NGINX_USER=$NGINX_USER"
  echo

  echo "===== htpasswd before ====="
  sudo ls -l /etc/nginx/oris-dev-employee.htpasswd || true
  sudo namei -l /etc/nginx/oris-dev-employee.htpasswd || true
  echo

  echo "===== fix htpasswd ownership and mode ====="
  sudo chown "root:${NGINX_USER}" /etc/nginx/oris-dev-employee.htpasswd || true
  sudo chmod 640 /etc/nginx/oris-dev-employee.htpasswd || true
  sudo -u "$NGINX_USER" test -r /etc/nginx/oris-dev-employee.htpasswd && echo "HTPASSWD_READABLE_BY_NGINX_USER" || echo "HTPASSWD_NOT_READABLE_BY_NGINX_USER"
  echo

  echo "===== htpasswd after ====="
  sudo ls -l /etc/nginx/oris-dev-employee.htpasswd || true
  sudo namei -l /etc/nginx/oris-dev-employee.htpasswd || true
  echo

  echo "===== nginx syntax and reload ====="
  sudo nginx -t || true
  sudo systemctl reload nginx || true
  systemctl is-active nginx || true
  echo

  echo "===== relevant nginx error logs ====="
  sudo tail -n 80 /var/log/nginx/oris-dev-employee-console.error.log 2>/dev/null || true
  sudo tail -n 80 /var/log/nginx/error.log 2>/dev/null || true
  echo

  echo "===== public unauth health should be 401 ====="
  curl -sS -o /tmp/orisfy_unauth_after_htpasswd.out -w '%{http_code}\n' https://control.orisfy.com/health || true
  cat /tmp/orisfy_unauth_after_htpasswd.out || true
  echo

  echo "===== public auth health should be 200 ====="
  curl -sS -u "$BA_USER:$BA_PASS" -o /tmp/orisfy_auth_health_after_htpasswd.out -w '%{http_code}\n' https://control.orisfy.com/health || true
  cat /tmp/orisfy_auth_health_after_htpasswd.out || true
  echo

  echo "===== public auth POST /api/goals should be 403 ====="
  curl -sS -u "$BA_USER:$BA_PASS" -X POST https://control.orisfy.com/api/goals \
    -H 'Content-Type: application/json' \
    -d '{}' \
    -o /tmp/orisfy_post_goals_after_htpasswd.out \
    -w '%{http_code}\n' || true
  cat /tmp/orisfy_post_goals_after_htpasswd.out || true
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
  git commit -m "test(dev-employee): verify orisfy htpasswd permission fix"
  git push origin main
fi

git log -1 --oneline
