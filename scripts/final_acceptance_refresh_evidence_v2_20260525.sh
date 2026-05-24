#!/usr/bin/env bash

ORIS_DIR="/home/admin/projects/oris"
PRODUCT_DIR="/home/admin/projects/oris-final-acceptance-api"
TMP_DIR="/tmp/oris-final-acceptance-evidence-20260525"
LOG_DIR="$ORIS_DIR/logs/dev_employee"
PY_COMPILE_TMP="$TMP_DIR/final_acceptance_py_compile_20260524.txt"
PYTEST_TMP="$TMP_DIR/final_acceptance_pytest_20260524.txt"
GIT_TMP="$TMP_DIR/final_acceptance_git_20260524.txt"
REFRESH_LOG="$TMP_DIR/final_acceptance_refresh_evidence_v2_20260525.log"

mkdir -p "$TMP_DIR" "$LOG_DIR"

{
  echo "===== refresh final acceptance evidence v2 ====="
  date -Iseconds

  echo "===== product checkout ====="
  cd "$PRODUCT_DIR" || exit 10
  git fetch origin main
  git reset --hard origin/main
  git status --short
  git log -1 --oneline

  echo "===== product file check ====="
  find app tests -maxdepth 2 -type f | sort
  test -f app/__init__.py || exit 20
  test -f app/main.py || exit 21

  echo "===== product python import check ====="
  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install -r requirements.txt
  PYTHONPATH="$PRODUCT_DIR" python - <<'PY' > "$TMP_DIR/final_acceptance_import_check_20260525.txt" 2>&1
import app
import app.main
print('IMPORT_OK')
print(app.main.app.title)
PY
  cat "$TMP_DIR/final_acceptance_import_check_20260525.txt"

  echo "===== checks to tmp files ====="
  PYTHONPATH="$PRODUCT_DIR" python3 -m py_compile app/main.py > "$PY_COMPILE_TMP" 2>&1
  PYTHONPATH="$PRODUCT_DIR" python -m pytest -q > "$PYTEST_TMP" 2>&1
  cat "$PYTEST_TMP"

  PRODUCT_SHA="$(git rev-parse HEAD)"
  {
    echo "PRODUCT_SHA=$PRODUCT_SHA"
    git remote -v
    git status --short
    git log -1 --oneline
  } > "$GIT_TMP" 2>&1

  echo "===== reset ORIS and restore evidence from tmp ====="
  cd "$ORIS_DIR" || exit 11
  git fetch origin main
  git reset --hard origin/main
  mkdir -p logs/dev_employee memory/dev_employee orchestration/task_runs
  cp "$PY_COMPILE_TMP" logs/dev_employee/final_acceptance_py_compile_20260524.txt
  cp "$PYTEST_TMP" logs/dev_employee/final_acceptance_pytest_20260524.txt
  cp "$GIT_TMP" logs/dev_employee/final_acceptance_git_20260524.txt

  python3 scripts/update_final_acceptance_registry_20260524.py "$PRODUCT_SHA"

  git add orchestration/project_registry.json memory/dev_employee/current_task.json memory/dev_employee/current_task.md logs/dev_employee/latest_task_progress.json logs/dev_employee/latest_task_progress.md logs/dev_employee/final_acceptance_py_compile_20260524.txt logs/dev_employee/final_acceptance_pytest_20260524.txt logs/dev_employee/final_acceptance_git_20260524.txt orchestration/task_runs/oris-final-acceptance-api-20260523.json

  if git diff --cached --quiet; then
    echo "NO_CHANGES_TO_COMMIT"
  else
    git commit -m "docs(registry): refresh passing final acceptance evidence"
    git push origin main
  fi

  cp "$REFRESH_LOG" "$LOG_DIR/final_acceptance_refresh_evidence_v2_20260525.log" 2>/dev/null || true

  echo "PRODUCT_SHA=$PRODUCT_SHA"
  echo "ORIS_SHA=$(git rev-parse HEAD)"
  echo "PYTEST_LOG_BEGIN"
  cat logs/dev_employee/final_acceptance_pytest_20260524.txt
  echo "PYTEST_LOG_END"
} 2>&1 | tee "$REFRESH_LOG"
