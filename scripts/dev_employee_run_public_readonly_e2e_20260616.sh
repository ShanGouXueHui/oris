#!/usr/bin/env bash

ORIS_DIR="/home/admin/projects/oris"
RUNNER="scripts/dev_employee_run_public_readonly_e2e_final_20260616.py"
PATCHER="scripts/dev_employee_patch_public_readonly_e2e_done_evidence_20260616.py"
PATCH_COMMIT=""

print_failure_summary() {
  local code="$1"
  local next="$2"
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID="
  echo "PUBLIC_SUBMIT_HTTP="
  echo "FINAL_STATUS=not_started"
  echo "CANONICAL_STATUS=not_started"
  echo "TERMINAL=false"
  echo "FAILURE_CODE=$code"
  echo "LOG_COMMIT="
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=$next"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

if [ "$(id -un)" != "admin" ]; then
  print_failure_summary "wrong_linux_user" "RUN_AS_ADMIN"
  exit 1
fi

cd "$ORIS_DIR" || {
  print_failure_summary "oris_directory_missing" "RESTORE_ORIS_REPOSITORY"
  exit 1
}

python3 "$PATCHER"
if [ "$?" -ne 0 ]; then
  print_failure_summary "evidence_aware_runner_patch_failed" "INSPECT_PATCHER"
  exit 1
fi

python3 -m py_compile "$PATCHER" "$RUNNER"
if [ "$?" -ne 0 ]; then
  print_failure_summary "public_e2e_runner_compile_failed" "FIX_RUNNER_STATIC_CHECK"
  exit 1
fi

git diff --check -- "$RUNNER"
if [ "$?" -ne 0 ]; then
  print_failure_summary "public_e2e_runner_diff_check_failed" "FIX_RUNNER_DIFF"
  exit 1
fi

git add -- "$RUNNER"
if [ "$?" -ne 0 ]; then
  print_failure_summary "public_e2e_runner_git_add_failed" "INSPECT_GIT_STATE"
  exit 1
fi

if git diff --cached --quiet -- "$RUNNER"; then
  PATCH_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
else
  git commit --only -m "fix(dev-employee): wait for completed evidence index" -- "$RUNNER"
  if [ "$?" -ne 0 ]; then
    print_failure_summary "public_e2e_runner_commit_failed" "INSPECT_GIT_COMMIT"
    exit 1
  fi
  PATCH_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  git push origin main
  if [ "$?" -ne 0 ]; then
    print_failure_summary "public_e2e_runner_push_failed" "RESOLVE_ORIS_GIT_PUSH"
    exit 1
  fi
fi

REMOTE_SHA="$(git ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
if [ -z "$PATCH_COMMIT" ] || [ "$REMOTE_SHA" != "$PATCH_COMMIT" ]; then
  print_failure_summary "public_e2e_runner_remote_sha_mismatch" "RESOLVE_ORIS_REMOTE_SHA"
  exit 1
fi

exec python3 "$RUNNER"
