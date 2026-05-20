#!/usr/bin/env bash

ROOT_DIR="${ORIS_REPO_DIR:-$HOME/projects/oris}"
BRANCH="${ORIS_BRANCH:-main}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
CONF="/etc/nginx/sites-enabled/control.orisfy.com.conf"
BACKUP="/tmp/control.orisfy.com.conf.before-openclaw-auth-mode.$TS"
OUT_JSON="logs/dev_employee/latest_openclaw_nginx_auth_mode.json"
OUT_MD="logs/dev_employee/latest_openclaw_nginx_auth_mode.md"

cd "$ROOT_DIR" || exit 1
mkdir -p logs/dev_employee

if [ ! -f "$CONF" ]; then
  echo "Nginx config not found: $CONF" >&2
  exit 2
fi

sudo cp -a "$CONF" "$BACKUP"

sudo python3 - <<PY
from pathlib import Path
conf = Path("$CONF")
text = conf.read_text()
marker = "proxy_pass http://127.0.0.1:18789;"
if marker not in text:
    raise SystemExit("OpenClaw proxy marker not found")
lines = text.splitlines()
out = []
in_target = False
inserted_off = False
for line in lines:
    stripped = line.strip()
    if stripped.startswith("location "):
        in_target = False
    if marker in stripped:
        in_target = True
        # Ensure auth is disabled in this gateway UI/ws proxy block. OpenClaw token/device pairing remains active.
        indent = line[:len(line) - len(line.lstrip())]
        if not inserted_off:
            out.append(f"{indent}auth_basic off;")
            inserted_off = True
        out.append(line)
        continue
    if in_target and (stripped.startswith("auth_basic ") or stripped.startswith("auth_basic_user_file ")):
        continue
    out.append(line)
conf.write_text("\n".join(out) + "\n")
PY

NGINX_TEST_OUTPUT="$(sudo nginx -t 2>&1)"
NGINX_RC=$?
if [ "$NGINX_RC" -eq 0 ]; then
  sudo systemctl reload nginx
else
  sudo cp -a "$BACKUP" "$CONF"
  sudo nginx -t >/dev/null 2>&1 || true
fi
sleep 2

python3 - <<PY > "$OUT_JSON"
import json, subprocess
from pathlib import Path

def run(cmd):
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return {"rc": p.returncode, "stdout": (p.stdout or "")[-5000:], "stderr": (p.stderr or "")[-3000:]}

payload = {
  "ok": int("$NGINX_RC") == 0,
  "timestamp_utc": "$TS",
  "conf": "$CONF",
  "backup": "$BACKUP",
  "nginx_test_rc": int("$NGINX_RC"),
  "nginx_test_output": '''$NGINX_TEST_OUTPUT''',
  "mode": "nginx_basic_auth_disabled_for_openclaw_gateway_block",
  "security_note": "OpenClaw gateway token/device pairing remains active; Nginx Basic Auth remains for other configured API locations.",
  "public_dashboard_head": run("curl -I --max-time 8 https://control.orisfy.com/ 2>&1 | tail -n 40"),
  "local_gateway_head": run("curl -I --max-time 5 http://127.0.0.1:18789/ 2>&1 | tail -n 40"),
  "nginx_openclaw_block": run("grep -nA32 -B6 'proxy_pass http://127.0.0.1:18789' /etc/nginx/sites-enabled/control.orisfy.com.conf"),
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY

cat > "$OUT_MD" <<EOF
# OpenClaw Nginx Auth Mode

- timestamp_utc: $TS
- ok: $([ "$NGINX_RC" -eq 0 ] && echo true || echo false)
- mode: auth_basic off for OpenClaw gateway block
- conf: $CONF
- backup: $BACKUP
- json: \`$OUT_JSON\`
EOF

git add "$OUT_JSON" "$OUT_MD" scripts/patch_nginx_openclaw_auth_mode.sh
if ! git diff --cached --quiet; then
  git commit -m "logs(openclaw): patch nginx auth mode for gateway UI" >/tmp/openclaw_nginx_auth_mode_git.log 2>&1 || true
fi

git pull --rebase origin "$BRANCH" >/tmp/openclaw_nginx_auth_mode_pull.log 2>&1 || true
git push origin "$BRANCH" >/tmp/openclaw_nginx_auth_mode_push.log 2>&1 || true

HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "OPENCLAW_NGINX_AUTH_MODE_REF=${HEAD_SHORT} ${OUT_JSON} ${OUT_MD}"
exit "$NGINX_RC"
