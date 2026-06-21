#!/usr/bin/env bash

REPO_DIR="${ORIS_REPO_DIR:-/home/admin/projects/oris}"
TASK_ID="${1:-${ORIS_DEMO_TASK_ID:-}}"
MAX_ROUNDS="${ORIS_DEMO_WAIT_ROUNDS:-30}"
SLEEP_SECONDS="${ORIS_DEMO_WAIT_SLEEP:-10}"

if [ -z "$TASK_ID" ]; then
  echo "ERROR: task id is required"
  echo "usage: bash runbooks/oris_demo_wait_and_verify.sh <TASK_ID>"
  exit 2
fi

cd "$REPO_DIR" || { echo "ERROR: ORIS repo not found: $REPO_DIR"; exit 10; }

echo "== wait for demo terminal =="
echo "TASK_ID=$TASK_ID"

for round in $(seq 1 "$MAX_ROUNDS"); do
  STATUS_FILE="/tmp/oris_demo_wait_${TASK_ID}_${round}.json"
  curl -sS "http://127.0.0.1:18892/goals/${TASK_ID}" > "$STATUS_FILE"
  python3 - "$STATUS_FILE" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(json.dumps({
    "status": data.get("status"),
    "canonical_status": data.get("canonical_status"),
    "terminal": data.get("terminal"),
    "failure_code": data.get("failure_code"),
}, ensure_ascii=False))
PY
  TERMINAL=$(python3 - "$STATUS_FILE" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("1" if data.get("terminal") else "0")
PY
)
  if [ "$TERMINAL" = "1" ]; then
    echo "== task is terminal =="
    break
  fi
  echo "== bridge once, round ${round}/${MAX_ROUNDS} =="
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts:. python3 scripts/dev_employee_supervised_bridge_v2.py || true
  sleep "$SLEEP_SECONDS"
done

echo "== queue files =="
ls -la orchestration/dev_employee_queue/*"$TASK_ID"* 2>/dev/null || true

echo "== run files =="
ls -la orchestration/task_runs/*"$TASK_ID"* 2>/dev/null || true

echo "== latest bridge logs =="
ls -la logs/dev_employee/*"$TASK_ID"* 2>/dev/null || true

echo "== final verifier =="
bash runbooks/oris_demo_verify_openclaw_result.sh "$TASK_ID"
