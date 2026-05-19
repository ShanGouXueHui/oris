#!/usr/bin/env bash

ROOT_DIR="${ORIS_REPO_DIR:-$HOME/projects/oris}"
BRANCH="${ORIS_BRANCH:-main}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_JSON="logs/dev_employee/latest_openclaw_safe_diag.json"
OUT_MD="logs/dev_employee/latest_openclaw_safe_diag.md"

cd "$ROOT_DIR" || exit 1
mkdir -p logs/dev_employee

python3 - <<'PY' > "$OUT_JSON"
import json
import subprocess
from pathlib import Path


def run(cmd: str, timeout: int = 20):
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": (p.stdout or "")[-12000:], "stderr": (p.stderr or "")[-6000:], "timeout": False}
    except subprocess.TimeoutExpired as e:
        return {"rc": 124, "stdout": (e.stdout or "")[-12000:] if isinstance(e.stdout, str) else "", "stderr": (e.stderr or "")[-6000:] if isinstance(e.stderr, str) else "", "timeout": True}


def load_json(path: str):
    p = Path(path).expanduser()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as e:
        return {"error": repr(e)}

cfg = load_json("~/.openclaw/openclaw.json")
defaults = ((cfg.get("agents") or {}).get("defaults") or {}) if isinstance(cfg, dict) else {}
summary = {
    "primary_model": ((defaults.get("model") or {}).get("primary")) if isinstance(defaults.get("model"), dict) else None,
    "model_keys": sorted((defaults.get("models") or {}).keys()) if isinstance(defaults.get("models"), dict) else [],
}

payload = {
    "ok": True,
    "summary": summary,
    "openclaw_status": run("systemctl --user status openclaw-gateway.service --no-pager -l | tail -n 100"),
    "free_mesh_status": run("systemctl --user status oris-free-mesh-api.service --no-pager -l | tail -n 60"),
    "ports": run("ss -lntp | grep -E '18789|8789' || true"),
    "local_gateway_head": run("curl -I --max-time 5 http://127.0.0.1:18789/ 2>&1 | tail -n 60", timeout=10),
    "public_dashboard_head": run("curl -I --max-time 8 https://control.orisfy.com/ 2>&1 | tail -n 60", timeout=12),
    "free_mesh_health": run("curl -sS --max-time 5 http://127.0.0.1:8789/v1/health", timeout=8),
    "openclaw_dashboard_timeout": run("timeout 15s openclaw dashboard 2>&1 | tail -n 160", timeout=20),
    "openclaw_gateway_status_timeout": run("timeout 15s openclaw gateway status --deep 2>&1 | tail -n 200", timeout=20),
    "recent_gateway_logs": run("journalctl --user -u openclaw-gateway.service -n 220 --no-pager", timeout=15),
    "nginx_control_config": run("grep -RInE 'server_name control\\.orisfy\\.com|proxy_pass|proxy_http_version|proxy_set_header Upgrade|proxy_set_header Connection|auth_basic|18789|control.orisfy.com' /etc/nginx/sites-enabled /etc/nginx/conf.d /etc/nginx/nginx.conf 2>/dev/null | tail -n 240"),
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY

cat > "$OUT_MD" <<EOF
# OpenClaw Safe Diagnostic

- generated_at: $TS
- json: $OUT_JSON
EOF

git add "$OUT_JSON" "$OUT_MD" scripts/openclaw_safe_diag.sh
if ! git diff --cached --quiet; then
  git commit -m "logs(openclaw): update safe diagnostic" >/tmp/openclaw_safe_diag_git.log 2>&1 || true
fi

git pull --rebase origin "$BRANCH" >/tmp/openclaw_safe_diag_pull.log 2>&1 || true
git push origin "$BRANCH" >/tmp/openclaw_safe_diag_push.log 2>&1 || true

HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "OPENCLAW_SAFE_DIAG_REF=${HEAD_SHORT} ${OUT_JSON} ${OUT_MD}"
