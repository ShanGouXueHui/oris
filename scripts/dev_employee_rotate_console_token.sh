#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
LOG_DIR="logs/dev_employee/web_console_token_rotation"
LOG_FILE="$LOG_DIR/rotate-console-token-$(date +%Y%m%d%H%M%S).log"
mkdir -p "$LOG_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing $ENV_FILE"
  exit 1
fi

NEW_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"

{
  echo "===== timestamp ====="
  date -Is
  echo
  echo "===== rotate token ====="
  cp "$ENV_FILE" "${ENV_FILE}.bak_$(date +%Y%m%d%H%M%S)"
  python3 - "$ENV_FILE" "$NEW_TOKEN" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
new_token = sys.argv[2]
lines = path.read_text(encoding="utf-8").splitlines()
out = []
replaced = False
for line in lines:
    if line.startswith("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN="):
        out.append("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=" + new_token)
        replaced = True
    else:
        out.append(line)
if not replaced:
    out.append("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=" + new_token)
path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY
  chmod 600 "$ENV_FILE"
  systemctl --user restart oris-dev-employee-web-console.service
  sleep 2
  echo "TOKEN_ROTATED=true"
  echo "TOKEN_VALUE_LOGGED=false"
  echo "WEB_CONSOLE_SERVICE=$(systemctl --user is-active oris-dev-employee-web-console.service 2>/dev/null || true)"
  echo
} | tee "$LOG_FILE"

git add "$LOG_FILE"
if git diff --cached --quiet; then
  COMMIT_RESULT="NO_LOG_CHANGES"
else
  git commit -m "test(dev-employee): rotate public console token"
  git push origin main
  COMMIT_RESULT="$(git rev-parse --short HEAD)"
fi

echo
echo "===== NEW CONSOLE TOKEN - COPY LOCALLY, DO NOT SEND ====="
echo "$NEW_TOKEN"
echo "===== END NEW CONSOLE TOKEN ====="
echo
echo "===== SUMMARY ====="
echo "RESULT=PASS"
echo "GIT_COMMIT=$COMMIT_RESULT"
echo "ACTION=console_token_rotated"
echo "WEB_CONSOLE_SERVICE=$(systemctl --user is-active oris-dev-employee-web-console.service 2>/dev/null || true)"
echo "TOKEN_VALUE_IN_GITHUB=false"
echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
echo "===== END SUMMARY ====="
