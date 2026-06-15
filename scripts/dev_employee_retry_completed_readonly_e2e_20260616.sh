#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
TASK_ID="${1:-goal-oris-final-acceptance-api-readonly-e2e-20260616-044030}"
STASHED="NO"

failure_summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$1"
  echo "REAL_PRODUCT_TASK_SUBMITTED=YES"
  echo "NEW_PRODUCT_TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=$2"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

if [ "$(id -un)" != "admin" ]; then
  failure_summary "wrong_linux_user" "RUN_AS_ADMIN"
  exit 1
fi

cd "$ORIS" || {
  failure_summary "oris_directory_missing" "RESTORE_ORIS_REPOSITORY"
  exit 1
}

if ! git diff --quiet -- scripts/dev_employee_diagnose_codex_failed_task.sh; then
  git stash push -m "temp-diagnose-before-completed-e2e-verification" -- scripts/dev_employee_diagnose_codex_failed_task.sh >/tmp/oris-e2e-stash.log 2>&1
  if [ "$?" -ne 0 ]; then
    failure_summary "diagnose_script_stash_failed" "INSPECT_GIT_STATE"
    exit 1
  fi
  STASHED="YES"
fi

git fetch origin main >/tmp/oris-e2e-fetch.log 2>&1
if [ "$?" -ne 0 ]; then
  [ "$STASHED" = "YES" ] && git stash pop >/dev/null 2>&1 || true
  failure_summary "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
  exit 1
fi

git rebase origin/main >/tmp/oris-e2e-rebase.log 2>&1
if [ "$?" -ne 0 ]; then
  failure_summary "oris_rebase_failed" "INSPECT_ORIS_REBASE"
  exit 1
fi

if [ "$STASHED" = "YES" ]; then
  git stash pop >/tmp/oris-e2e-stash-pop.log 2>&1
  if [ "$?" -ne 0 ]; then
    failure_summary "diagnose_script_stash_pop_failed" "INSPECT_GIT_STATE"
    exit 1
  fi
fi

python3 -m py_compile scripts/dev_employee_verify_completed_readonly_e2e_20260616.py
if [ "$?" -ne 0 ]; then
  failure_summary "completed_e2e_verifier_compile_failed" "FIX_VERIFIER_STATIC_CHECK"
  exit 1
fi

exec python3 scripts/dev_employee_verify_completed_readonly_e2e_20260616.py "$TASK_ID"
