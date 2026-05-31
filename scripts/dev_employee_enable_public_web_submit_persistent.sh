#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

SERVICE="$HOME/.config/systemd/user/oris-dev-employee-web-console.service"
ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
NGINX_CONF="/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf"
LOG_DIR="logs/dev_employee/web_console_public_submit_persistent"
LOG_FILE="$LOG_DIR/enable-public-web-submit-persistent-$(date +%Y%m%d%H%M%S).log"
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

  echo "===== explicit policy ====="
  echo "PUBLIC_WEB_SUBMIT_MODE=persistent"
  echo "PUBLIC_ENTRY=https://control.orisfy.com"
  echo "REQUIRED_OUTER_AUTH=BasicAuth"
  echo "REQUIRED_INNER_AUTH=X-ORIS-Console-Token"
  echo "PROJECT_ALLOWLIST=oris-final-acceptance-api"
  echo "INTAKE_DIRECT_PUBLIC_EXPOSURE=forbidden"
  echo "PUBLIC_POST_ALLOWED_PATH=/api/goals only"
  echo

  echo "===== current nginx config before ====="
  sudo grep -n 'location = /api/goals\|request_method\|proxy_pass http://127.0.0.1:18893\|127.0.0.1:18892\|auth_basic' "$NGINX_CONF" || true
  echo

  echo "===== current service before ====="
  grep 'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED\|ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST' "$SERVICE" || true
  echo

  echo "===== enable persistent public submit safely ====="
  TS="$(date +%Y%m%d%H%M%S)"
  sudo cp "$NGINX_CONF" "${NGINX_CONF}.bak_persistent_public_submit_${TS}"
  echo "NGINX_BACKUP=${NGINX_CONF}.bak_persistent_public_submit_${TS}"
  sudo python3 - <<'PY'
from pathlib import Path
p = Path('/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf')
text = p.read_text(encoding='utf-8')
# Only allow POST on the exact /api/goals endpoint. Other locations stay GET/HEAD-only.
old = 'location = /api/goals {\n        if ($request_method !~ ^(GET)$) { return 403; }'
new = 'location = /api/goals {\n        if ($request_method !~ ^(GET|POST)$) { return 403; }'
if old in text:
    text = text.replace(old, new, 1)
elif new in text:
    pass
else:
    raise SystemExit('expected /api/goals guard not found')
if 'proxy_pass http://127.0.0.1:18892' in text:
    raise SystemExit('refusing config that proxies direct intake')
p.write_text(text, encoding='utf-8')
PY
  python3 - <<'PY'
from pathlib import Path
import re
from datetime import datetime
svc = Path.home() / '.config' / 'systemd' / 'user' / 'oris-dev-employee-web-console.service'
text = svc.read_text(encoding='utf-8')
backup = svc.with_suffix(svc.suffix + f'.bak_persistent_public_submit_{datetime.now().strftime("%Y%m%d%H%M%S")}')
backup.write_text(text, encoding='utf-8')
updates = {
    'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED': '1',
    'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST': 'oris-final-acceptance-api',
}
for key, value in updates.items():
    pattern = rf'^Environment={re.escape(key)}=.*$'
    replacement = f'Environment={key}={value}'
    if re.search(pattern, text, flags=re.MULTILINE):
        text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    else:
        text = text.replace('[Service]\n', f'[Service]\n{replacement}\n', 1)
svc.write_text(text, encoding='utf-8')
print(f'SERVICE_BACKUP={backup}')
PY
  sudo nginx -t
  sudo systemctl reload nginx
  systemctl --user daemon-reload
  systemctl --user restart oris-dev-employee-web-console.service
  sleep 2
  echo

  echo "===== nginx config after ====="
  sudo grep -n 'location = /api/goals\|request_method\|proxy_pass http://127.0.0.1:18893\|127.0.0.1:18892\|auth_basic' "$NGINX_CONF" || true
  echo

  echo "===== service after ====="
  grep 'ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED\|ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST' "$SERVICE" || true
  echo

  echo "===== token presence only; token not logged ====="
  if [ -f "$ENV_FILE" ]; then
    grep -q '^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=' "$ENV_FILE" && echo "CONSOLE_TOKEN_PRESENT" || echo "CONSOLE_TOKEN_MISSING"
    grep -q '^ORIS_DEV_EMPLOYEE_INTAKE_TOKEN=' "$ENV_FILE" && echo "INTAKE_TOKEN_PRESENT" || echo "INTAKE_TOKEN_MISSING"
  else
    echo "ENV_FILE_MISSING=$ENV_FILE"
  fi
  echo

  echo "===== public route checks without secrets ====="
  echo "unauth health should be 401"
  curl -sS -o /tmp/orisfy_persistent_unauth_health.out -w '%{http_code}\n' https://control.orisfy.com/health || true
  cat /tmp/orisfy_persistent_unauth_health.out || true
  echo
  echo "unauth POST /api/goals should be 401 from Basic Auth, not reach app"
  curl -sS -o /tmp/orisfy_persistent_unauth_post.out -w '%{http_code}\n' -X POST https://control.orisfy.com/api/goals -H 'Content-Type: application/json' -d '{}' || true
  cat /tmp/orisfy_persistent_unauth_post.out || true
  echo

  echo "===== final local services ====="
  systemctl --user is-active oris-dev-employee-web-console.service || true
  systemctl --user is-active oris-dev-employee-intake.service || true
  systemctl --user is-active oris-dev-employee-bridge.service || true
  echo
} | tee "$LOG_FILE"

git add "$LOG_FILE"
if git diff --cached --quiet; then
  echo "NO_LOG_CHANGES_TO_COMMIT"
else
  git commit -m "test(dev-employee): enable persistent public web submit"
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
echo "===== PUBLIC WEB UI ====="
echo "Open: https://control.orisfy.com"
echo "Use Basic Auth first, then paste the Console Token above into the Web UI token field."
echo "Allowed project: oris-final-acceptance-api"
echo "Public submit is now persistent, but still protected by Basic Auth + Console Token + project allowlist."
echo
git log -1 --oneline
