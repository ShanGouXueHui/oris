#!/usr/bin/env bash

ORIS_DIR="/home/admin/projects/oris"
PRODUCT_DIR="/home/admin/projects/oris-final-acceptance-api"
LOG_DIR="$ORIS_DIR/logs/dev_employee"
PY_COMPILE_LOG="$LOG_DIR/final_acceptance_py_compile_20260524.txt"
PYTEST_LOG="$LOG_DIR/final_acceptance_pytest_20260524.txt"
REFRESH_LOG="$LOG_DIR/final_acceptance_refresh_evidence_20260525.log"

mkdir -p "$LOG_DIR"

{
  echo "===== refresh final acceptance evidence ====="
  date -Iseconds

  cd "$PRODUCT_DIR" || exit 10
  git fetch origin main
  git reset --hard origin/main

  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install -r requirements.txt

  python3 -m py_compile app/main.py > "$PY_COMPILE_LOG" 2>&1
  PYTHONPATH="$PRODUCT_DIR" python -m pytest -q > "$PYTEST_LOG" 2>&1

  PRODUCT_SHA="$(git rev-parse HEAD)"

  cd "$ORIS_DIR" || exit 11
  git fetch origin main
  git reset --hard origin/main

  mkdir -p logs/dev_employee memory/dev_employee orchestration/task_runs
  cp "$PY_COMPILE_LOG" logs/dev_employee/final_acceptance_py_compile_20260524.txt
  cp "$PYTEST_LOG" logs/dev_employee/final_acceptance_pytest_20260524.txt

  python3 scripts/update_final_acceptance_registry_20260524.py "$PRODUCT_SHA"

  git add orchestration/project_registry.json memory/dev_employee/current_task.json memory/dev_employee/current_task.md logs/dev_employee/latest_task_progress.json logs/dev_employee/latest_task_progress.md logs/dev_employee/final_acceptance_py_compile_20260524.txt logs/dev_employee/final_acceptance_pytest_20260524.txt orchestration/task_runs/oris-final-acceptance-api-20260523.json

  if git diff --cached --quiet; then
    echo "NO_CHANGES_TO_COMMIT"
  else
    git commit -m "docs(registry): refresh passing final acceptance evidence"
    git push origin main
  fi

  echo "PRODUCT_SHA=$PRODUCT_SHA"
  echo "ORIS_SHA=$(git rev-parse HEAD)"
  echo "PYTEST_LOG_BEGIN"
  cat logs/dev_employee/final_acceptance_pytest_20260524.txt
  echo "PYTEST_LOG_END"
} 2>&1 | tee "$REFRESH_LOG"
