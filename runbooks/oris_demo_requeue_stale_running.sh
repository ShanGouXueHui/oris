#!/usr/bin/env bash

REPO_DIR="${ORIS_REPO_DIR:-/home/admin/projects/oris}"
TASK_ID="${1:-${ORIS_DEMO_TASK_ID:-}}"

if [ -z "$TASK_ID" ]; then
  echo "ERROR: task id is required"
  echo "usage: bash runbooks/oris_demo_requeue_stale_running.sh <TASK_ID>"
  exit 2
fi

cd "$REPO_DIR" || { echo "ERROR: ORIS repo not found: $REPO_DIR"; exit 10; }

RUNNING="orchestration/dev_employee_queue/${TASK_ID}.running.json"
QUEUED="orchestration/dev_employee_queue/${TASK_ID}.queued.json"
RUN_JSON="orchestration/task_runs/${TASK_ID}.json"
CODEX_JSON="orchestration/task_runs/${TASK_ID}.codex_result.json"

if [ ! -f "$RUNNING" ]; then
  echo "ERROR: running descriptor not found: $RUNNING"
  exit 11
fi

if [ -f "$RUN_JSON" ] || [ -f "$CODEX_JSON" ]; then
  echo "ERROR: run output already exists; refusing to requeue"
  ls -la "$RUN_JSON" "$CODEX_JSON" 2>/dev/null || true
  exit 12
fi

if pgrep -af "$TASK_ID" | grep -v "oris_demo_requeue_stale_running" >/tmp/oris_demo_active_${TASK_ID}.txt 2>/dev/null; then
  echo "ERROR: active process still references this task; refusing to requeue"
  cat /tmp/oris_demo_active_${TASK_ID}.txt
  exit 13
fi

python3 - "$RUNNING" "$QUEUED" <<'PY'
import json
import sys
from pathlib import Path

running = Path(sys.argv[1])
queued = Path(sys.argv[2])
data = json.loads(running.read_text(encoding="utf-8"))
data["status"] = "queued"
data["requeued_from_stale_running"] = True
data.pop("started_at", None)
queued.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
running.unlink()
PY

echo "== requeued =="
ls -la "$QUEUED"

echo "== run bridge once =="
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts:. python3 scripts/dev_employee_supervised_bridge_v2.py

echo "== verify =="
bash runbooks/oris_demo_verify_openclaw_result.sh "$TASK_ID"
