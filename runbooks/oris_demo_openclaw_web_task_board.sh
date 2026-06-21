#!/usr/bin/env bash

REPO_DIR="${ORIS_REPO_DIR:-/home/admin/projects/oris}"
INTAKE_URL="${ORIS_INTAKE_URL:-http://127.0.0.1:18892/goals}"
ENV_FILE="${ORIS_ENV_FILE:-$HOME/.config/oris/dev_employee_enqueue.env}"
TASK_ID="${ORIS_DEMO_TASK_ID:-demo-openclaw-web-task-board-$(date +%Y%m%d%H%M%S)}"
PAYLOAD="/tmp/${TASK_ID}.payload.json"
RESPONSE="/tmp/${TASK_ID}.response.json"
RUN_BRIDGE_ONCE="${ORIS_DEMO_RUN_BRIDGE_ONCE:-1}"

cd "$REPO_DIR" || { echo "ERROR: repo not found: $REPO_DIR"; exit 10; }

if [ -f "$ENV_FILE" ]; then
  . "$ENV_FILE"
fi

if [ -z "${ORIS_DEV_EMPLOYEE_INTAKE_TOKEN:-}" ]; then
  echo "ERROR: ORIS_DEV_EMPLOYEE_INTAKE_TOKEN is missing. Checked: $ENV_FILE"
  exit 12
fi

python3 - "$PAYLOAD" "$TASK_ID" <<'PY'
import json
import sys

payload_path = sys.argv[1]
task_id = sys.argv[2]
payload = {
    "project_key": "oris-final-acceptance-api",
    "task_id": task_id,
    "objective": (
        "Demo project test from OpenClaw Web observation flow. In the FastAPI task-board API project, "
        "add a read-only health metadata endpoint GET /healthz/details returning service name, version, "
        "storage mode, and task count. Add or update pytest coverage. Preserve existing API behavior. "
        "Run compile and pytest checks. Commit changes with evidence."
    ),
    "constraints": [
        "Do not touch production services",
        "Do not change existing public API behavior except adding GET /healthz/details",
        "Do not hardcode secrets or environment-specific credentials",
        "Keep implementation minimal and testable",
    ],
    "expected_checks": [
        "python -m compileall .",
        "python -m pytest -q",
        "python -m pytest -q -W error",
    ],
    "commit_message": "feat(demo): add task-board health metadata endpoint",
}
with open(payload_path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
PY

printf '== submit demo task ==\n'
echo "TASK_ID=$TASK_ID"

curl -sS -X POST "$INTAKE_URL" \
  -H "Content-Type: application/json" \
  -H "X-ORIS-Token: ${ORIS_DEV_EMPLOYEE_INTAKE_TOKEN}" \
  --data-binary "@$PAYLOAD" | tee "$RESPONSE"

echo
python3 - "$RESPONSE" <<'PY'
import json
import sys

path = sys.argv[1]
try:
    data = json.load(open(path, encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: invalid response JSON: {exc}")
    raise SystemExit(21)
if data.get("error"):
    print(f"ERROR: intake rejected request: {data}")
    raise SystemExit(22)
print("== submit accepted ==")
print(json.dumps({
    "task_id": data.get("task_id"),
    "status": data.get("status"),
    "runtime_prompt_path": data.get("runtime_prompt_path"),
    "enqueue_http_status": data.get("enqueue_http_status"),
}, ensure_ascii=False, indent=2))
PY

if [ "$RUN_BRIDGE_ONCE" = "1" ]; then
  echo "== run supervised bridge once =="
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts:. python3 scripts/dev_employee_supervised_bridge_v2.py
fi

echo "== task status snapshot =="
curl -sS "http://127.0.0.1:18892/goals/${TASK_ID}" | python3 -m json.tool || true

cat <<EOF

== OpenClaw Web prompt ==
请使用 ORIS read-only tools 查询任务状态：

task_id = ${TASK_ID}

请返回：canonical status、terminal、product_commit_sha、evidence 文件、测试结果；如果失败，返回 failure_code 和 next_recommended_action。只读取状态，不提交新任务，不修改代码。
EOF
