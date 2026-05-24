#!/usr/bin/env bash

ORIS_DIR="/home/admin/projects/oris"
PRODUCT_DIR="/home/admin/projects/oris-final-acceptance-api"
LOG_DIR="$ORIS_DIR/logs/dev_employee"
mkdir -p "$LOG_DIR"

PY_COMPILE_LOG="$LOG_DIR/final_acceptance_py_compile_20260524.txt"
PYTEST_LOG="$LOG_DIR/final_acceptance_pytest_20260524.txt"
GIT_LOG="$LOG_DIR/final_acceptance_git_20260524.txt"
REPAIR_LOG="$LOG_DIR/final_acceptance_repair_and_push_20260524.log"

{
  echo "===== start ====="
  date -Iseconds

  cd "$PRODUCT_DIR" || exit 10
  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt

  python3 -m py_compile app/main.py > "$PY_COMPILE_LOG" 2>&1
  pytest -q > "$PYTEST_LOG" 2>&1

  {
    gh repo view ShanGouXueHui/oris-final-acceptance-api >/dev/null 2>&1 || gh repo create ShanGouXueHui/oris-final-acceptance-api --public --description "ORIS final acceptance FastAPI task-board API" --confirm
    git remote remove origin 2>/dev/null || true
    git remote add origin git@github.com:ShanGouXueHui/oris-final-acceptance-api.git
    git branch -M main
    git push -u origin main
    git rev-parse HEAD
  } > "$GIT_LOG" 2>&1

  PRODUCT_SHA="$(git rev-parse HEAD)"

  cd "$ORIS_DIR" || exit 11
  python3 scripts/update_final_acceptance_registry_20260524.py "$PRODUCT_SHA"

  git add orchestration/project_registry.json memory/dev_employee/current_task.json memory/dev_employee/current_task.md logs/dev_employee/latest_task_progress.json logs/dev_employee/latest_task_progress.md logs/dev_employee/final_acceptance_py_compile_20260524.txt logs/dev_employee/final_acceptance_pytest_20260524.txt logs/dev_employee/final_acceptance_git_20260524.txt logs/dev_employee/final_acceptance_repair_and_push_20260524.log orchestration/task_runs/oris-final-acceptance-api-20260523.json
  git commit -m "docs(registry): complete final acceptance API"
  git push origin main

  echo "PRODUCT_SHA=$PRODUCT_SHA"
  echo "ORIS_SHA=$(git rev-parse HEAD)"
} 2>&1 | tee "$REPAIR_LOG"
