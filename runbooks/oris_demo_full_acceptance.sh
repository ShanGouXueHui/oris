#!/usr/bin/env bash

REPO_DIR="${ORIS_REPO_DIR:-/home/admin/projects/oris}"
PRODUCT_DIR="${ORIS_DEMO_PRODUCT_DIR:-/home/admin/projects/oris-final-acceptance-api}"
TASK_ID="${ORIS_DEMO_TASK_ID:-demo-openclaw-web-task-board-$(date +%Y%m%d%H%M%S)}"

cd "$REPO_DIR" || { echo "ERROR: ORIS repo not found: $REPO_DIR"; exit 10; }

echo "== pull latest ORIS runbooks =="
git pull --ff-only origin main

echo "== preflight product venv =="
cd "$PRODUCT_DIR" || { echo "ERROR: product repo not found: $PRODUCT_DIR"; exit 20; }
if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -q --upgrade pip
if [ -f requirements.txt ]; then
  .venv/bin/python -m pip install -q -r requirements.txt
else
  .venv/bin/python -m pip install -q fastapi httpx pytest uvicorn
fi
.venv/bin/python -m pytest -q || exit 30

cd "$REPO_DIR" || exit 10

echo "== submit fresh demo task =="
echo "TASK_ID=$TASK_ID"
ORIS_DEMO_TASK_ID="$TASK_ID" ORIS_DEMO_RUN_BRIDGE_ONCE=1 bash runbooks/oris_demo_openclaw_web_task_board.sh || exit 40

echo "== verify fresh demo task =="
bash runbooks/oris_demo_verify_openclaw_result.sh "$TASK_ID" || exit 50

echo "== DEMO_TASK_ID =="
echo "$TASK_ID"
