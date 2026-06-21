#!/usr/bin/env bash

REPO_DIR="${ORIS_REPO_DIR:-/home/admin/projects/oris}"
PRODUCT_DIR="${ORIS_DEMO_PRODUCT_DIR:-/home/admin/projects/oris-final-acceptance-api}"
TASK_ID="${1:-${ORIS_DEMO_TASK_ID:-}}"
STATUS_JSON="/tmp/oris_demo_status_${TASK_ID}.json"
PRODUCT_CHECK_LOG="/tmp/oris_demo_product_checks_${TASK_ID}.log"

if [ -z "$TASK_ID" ]; then
  echo "ERROR: task id is required"
  echo "usage: bash runbooks/oris_demo_verify_openclaw_result.sh <TASK_ID>"
  exit 2
fi

cd "$REPO_DIR" || { echo "ERROR: ORIS repo not found: $REPO_DIR"; exit 10; }

echo "== ORIS demo verify =="
echo "TASK_ID=$TASK_ID"
echo "ORIS_HEAD=$(git rev-parse HEAD)"

echo "== intake status =="
curl -sS "http://127.0.0.1:18892/goals/${TASK_ID}" | tee "$STATUS_JSON" | python3 -m json.tool

python3 - "$STATUS_JSON" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
print("== parsed status summary ==")
if data.get("error"):
    print(json.dumps({"error": data.get("error"), "message": data.get("message")}, indent=2, ensure_ascii=False))
    raise SystemExit(20)
evidence = data.get("github_evidence") or {}
print(json.dumps({
    "task_id": data.get("task_id"),
    "status": data.get("status"),
    "canonical_status": data.get("canonical_status"),
    "terminal": data.get("terminal"),
    "failure_code": data.get("failure_code"),
    "product_commit_sha": evidence.get("product_commit_sha"),
    "product_remote_sha": evidence.get("product_remote_sha"),
    "oris_evidence_sha": evidence.get("oris_evidence_commit_sha") or evidence.get("oris_evidence_sha"),
    "evidence_files": len(evidence.get("files") or []),
}, indent=2, ensure_ascii=False))
PY

echo "== ORIS task run evidence files =="
ls -la "orchestration/task_runs/${TASK_ID}.json" "orchestration/task_runs/${TASK_ID}.codex_result.json" 2>/dev/null || true

echo "== product repo checks =="
cd "$PRODUCT_DIR" || { echo "ERROR: product repo not found: $PRODUCT_DIR"; exit 30; }
echo "PRODUCT_HEAD=$(git rev-parse HEAD)"
echo "PRODUCT_STATUS_SHORT=$(git status --short | wc -l) changed lines"
git status --short

if [ -x ".venv/bin/python" ]; then
  PRODUCT_PY=".venv/bin/python"
else
  python3 -m venv .venv
  PRODUCT_PY=".venv/bin/python"
fi

if ! "$PRODUCT_PY" -m pytest --version >/dev/null 2>&1; then
  echo "== install product test dependencies into .venv =="
  "$PRODUCT_PY" -m pip install -q --upgrade pip
  if [ -f requirements.txt ]; then
    "$PRODUCT_PY" -m pip install -q -r requirements.txt
  else
    "$PRODUCT_PY" -m pip install -q fastapi httpx pytest uvicorn
  fi
fi

{
  echo "-- python --"
  "$PRODUCT_PY" --version
  echo "-- compileall --"
  "$PRODUCT_PY" -m compileall .
  echo "-- pytest -q --"
  "$PRODUCT_PY" -m pytest -q
  echo "-- pytest -q -W error --"
  "$PRODUCT_PY" -m pytest -q -W error
} 2>&1 | tee "$PRODUCT_CHECK_LOG"
CHECK_RC=${PIPESTATUS[0]}
if [ "$CHECK_RC" -ne 0 ]; then
  echo "ERROR: product checks failed"
  echo "PRODUCT_CHECK_LOG=$PRODUCT_CHECK_LOG"
  exit 50
fi

if grep -R "healthz/details" -n . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=__pycache__ >/tmp/oris_demo_healthz_grep.txt 2>/dev/null; then
  echo "== endpoint grep =="
  cat /tmp/oris_demo_healthz_grep.txt
else
  echo "ERROR: /healthz/details not found in product repo"
  exit 40
fi

echo "== final verdict =="
python3 - "$STATUS_JSON" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
status = data.get("canonical_status") or data.get("status")
terminal = data.get("terminal")
evidence = data.get("github_evidence") or {}
files = evidence.get("files") or []
product_sha = evidence.get("product_commit_sha")
status_accept = status in {"success", "completed", "done"} or data.get("status") in {"completed", "done"}
print(json.dumps({
    "status_accept": status_accept,
    "terminal": terminal,
    "has_product_commit_sha": bool(product_sha),
    "has_evidence_files": bool(files),
    "product_commit_sha": product_sha,
    "note": "product_commit_sha is required for full Dev Employee acceptance; product checks may still pass locally without evidence commit.",
}, indent=2, ensure_ascii=False))
PY

echo "PRODUCT_CHECK_LOG=$PRODUCT_CHECK_LOG"
echo "STATUS_JSON=$STATUS_JSON"
