#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
RUNNER="/tmp/oris-apply-source-runtime-recovery-$$.sh"
HELPER="/tmp/oris-three-way-source-merge-$$.py"

summary_failure() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=resume-source-and-runtime-stash-recovery-20260617"
  echo "FAILURE_CODE=$1"
  echo "STASH_MUTATED=NO"
  echo "SERVICES_CHANGED=NO"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$2"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

cleanup() {
  rm -f "$RUNNER" "$HELPER"
}

if [ "$(id -un)" != "admin" ]; then
  summary_failure "wrong_linux_user" "RUN_AS_ADMIN"
  exit 1
fi

cd "$ORIS" || {
  summary_failure "oris_directory_missing" "RESTORE_ORIS_REPOSITORY"
  exit 1
}

git fetch origin main >/tmp/oris-source-runtime-resume-fetch.log 2>&1
if [ "$?" -ne 0 ]; then
  summary_failure "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
  exit 1
fi

git show origin/main:scripts/dev_employee_apply_source_runtime_recovery_20260617.sh > "$RUNNER"
if [ "$?" -ne 0 ] || [ ! -s "$RUNNER" ]; then
  cleanup
  summary_failure "recovery_runner_materialize_failed" "RESTORE_RECOVERY_RUNNER"
  exit 1
fi

git show origin/main:scripts/dev_employee_three_way_source_merge.py > "$HELPER"
if [ "$?" -ne 0 ] || [ ! -s "$HELPER" ]; then
  cleanup
  summary_failure "merge_helper_materialize_failed" "RESTORE_MERGE_HELPER"
  exit 1
fi

python3 - "$RUNNER" "$HELPER" <<'PY'
from pathlib import Path
import sys

runner = Path(sys.argv[1])
helper = Path(sys.argv[2])
text = runner.read_text(encoding="utf-8")
old = "python3 scripts/dev_employee_three_way_source_merge.py"
new = f"python3 {helper}"
if text.count(old) != 1:
    raise SystemExit(f"helper invocation anchor count={text.count(old)}")
runner.write_text(text.replace(old, new, 1), encoding="utf-8")
PY
if [ "$?" -ne 0 ]; then
  cleanup
  summary_failure "recovery_runner_patch_failed" "FIX_RECOVERY_WRAPPER"
  exit 1
fi

python3 -m py_compile "$HELPER" >/tmp/oris-source-runtime-helper-compile.log 2>&1
if [ "$?" -ne 0 ]; then
  cleanup
  summary_failure "merge_helper_compile_failed" "FIX_MERGE_HELPER"
  exit 1
fi

bash -n "$RUNNER" >/tmp/oris-source-runtime-runner-syntax.log 2>&1
if [ "$?" -ne 0 ]; then
  cleanup
  summary_failure "recovery_runner_syntax_failed" "FIX_RECOVERY_RUNNER"
  exit 1
fi

bash "$RUNNER"
RC="$?"
cleanup
exit "$RC"
