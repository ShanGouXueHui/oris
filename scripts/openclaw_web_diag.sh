#!/usr/bin/env bash

ROOT_DIR="${ORIS_REPO_DIR:-$HOME/projects/oris}"
BRANCH="${ORIS_BRANCH:-main}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_JSON="logs/dev_employee/latest_openclaw_web_diag.json"
OUT_MD="logs/dev_employee/latest_openclaw_web_diag.md"
RAW_DIR="run/openclaw_web_diag/$TS"

cd "$ROOT_DIR" || exit 1
mkdir -p logs/dev_employee "$RAW_DIR"

python3 - <<'PY' > "$OUT_JSON"
import json
import subprocess
from pathlib import Path


def run(cmd: str):
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return {
        "rc": p.returncode,
        "stdout": (p.stdout or "")[-8000:],
        "stderr": (p.stderr or "")[-4000:],
    }


def load_json(path: str):
    p = Path(path).expanduser()
    if not p.exists():
        return {"exists": False}
    try:
        return json.loads(p.read_text())
    except Exception as e:
        return {"exists": True, "error": repr(e)}

cfg = load_json("~/.openclaw/openclaw.json")
model_primary = None
model_keys = []
try:
    defaults = ((cfg.get("agents") or {}).get("defaults") or {})
    model_primary = ((defaults.get("model") or {}).get("primary"))
    if isinstance(defaults.get("models"), dict):
        model_keys = sorted(defaults.get("models").keys())
except Exception:
    pass

payload = {
    "ok": True,
    "summary": {
        "dashboard": "https://control.orisfy.com/",
        "gateway_local": "http://127.0.0.1:18789/",
        "free_mesh_local": "http://127.0.0.1:8789/v1",
        "openclaw_primary_model": model_primary,
        "openclaw_model_keys": model_keys,
    },
    "openclaw_status": run("systemctl --user status openclaw-gateway.service --no-pager -l | tail -n 80"),
    "openclaw_recent_logs": run("journalctl --user -u openclaw-gateway.service -n 160 --no-pager"),
    "free_mesh_status": run("systemctl --user status oris-free-mesh-api.service --no-pager -l | tail -n 60"),
    "local_gateway_head": run("curl -I --max-time 5 http://127.0.0.1:18789/ 2>&1 | tail -n 60"),
    "public_dashboard_root_head": run("curl -I --max-time 8 https://control.orisfy.com/ 2>&1 | tail -n 60"),
    "public_dashboard_chat_head": run("curl -I --max-time 8 'https://control.orisfy.com/chat' 2>&1 | tail -n 60"),
    "free_mesh_health": run("curl -sS --max-time 5 http://127.0.0.1:8789/v1/health"),
    "openclaw_dashboard_cmd": run("openclaw dashboard 2>&1 | tail -n 80"),
    "openclaw_doctor": run("openclaw doctor 2>&1 | tail -n 120"),
    "nginx_control_config": run("grep -RInE 'server_name control\\.orisfy\\.com|proxy_pass|proxy_http_version|proxy_set_header Upgrade|proxy_set_header Connection|auth_basic|18789|control.orisfy.com' /etc/nginx/sites-enabled /etc/nginx/conf.d /etc/nginx/nginx.conf 2>/dev/null | tail -n 240"),
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY

cat > "$OUT_MD" <<EOF
# OpenClaw Web Dashboard Diagnostic

- generated_at: $TS
- dashboard: https://control.orisfy.com/
- gateway: http://127.0.0.1:18789/
- free_mesh: http://127.0.0.1:8789/v1

See JSON: \\`$OUT_JSON\\`
EOF

git add "$OUT_JSON" "$OUT_MD" scripts/openclaw_web_diag.sh
if ! git diff --cached --quiet; then
  git commit -m "logs(openclaw): update web dashboard diagnostic" >/tmp/openclaw_web_diag_git.log 2>&1 || true
fi

git pull --rebase origin "$BRANCH" >/tmp/openclaw_web_diag_pull.log 2>&1 || true
git push origin "$BRANCH" >/tmp/openclaw_web_diag_push.log 2>&1 || true

HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "OPENCLAW_WEB_DIAG_REF=${HEAD_SHORT} ${OUT_JSON} ${OUT_MD}"
