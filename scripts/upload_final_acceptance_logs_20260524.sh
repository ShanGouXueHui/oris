#!/usr/bin/env bash

ORIS_DIR="/home/admin/projects/oris"
PRODUCT_DIR="/home/admin/projects/oris-final-acceptance-api"
LOG_DIR="$ORIS_DIR/logs/dev_employee"
UPLOAD_LOG="$LOG_DIR/upload_final_acceptance_logs_20260524.log"

mkdir -p "$LOG_DIR"

{
  echo "===== upload final acceptance logs ====="
  date -Iseconds
  whoami
  pwd
  echo

  cd "$ORIS_DIR" || exit 10

  echo "===== collect current repo state ====="
  {
    echo "===== ORIS git status ====="
    git status --short
    echo
    echo "===== ORIS head ====="
    git log -1 --oneline
    echo
    echo "===== product repo status ====="
    if [ -d "$PRODUCT_DIR/.git" ]; then
      cd "$PRODUCT_DIR" || exit 11
      git status --short
      git log -1 --oneline
      git rev-parse HEAD
    else
      echo "PRODUCT_REPO_NOT_FOUND: $PRODUCT_DIR"
    fi
  } > "$LOG_DIR/final_acceptance_repo_state_20260524.txt" 2>&1

  cd "$ORIS_DIR" || exit 12

  echo "===== add log files only ====="
  git add \
    logs/dev_employee/final_acceptance_codex_run_20260524.log \
    logs/dev_employee/final_acceptance_repair_and_push_20260524.log \
    logs/dev_employee/final_acceptance_py_compile_20260524.txt \
    logs/dev_employee/final_acceptance_pytest_20260524.txt \
    logs/dev_employee/final_acceptance_git_20260524.txt \
    logs/dev_employee/final_acceptance_repo_state_20260524.txt \
    logs/dev_employee/upload_final_acceptance_logs_20260524.log 2>/dev/null || true

  git status --short

  if git diff --cached --quiet; then
    echo "NO_LOG_CHANGES_TO_COMMIT"
  else
    git commit -m "logs(dev-employee): upload final acceptance logs"
    git push origin main
  fi

  echo "===== done ====="
  git log -1 --oneline
} 2>&1 | tee "$UPLOAD_LOG"
