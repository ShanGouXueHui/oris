#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
STAMP="$(date +%Y%m%d%H%M%S)"
RUNNER="/tmp/oris-intent-pythonpath-runner-$STAMP.sh"

summary_failure() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=resume-intent-boundary-with-pythonpath-20260617"
  echo "FAILURE_CODE=$1"
  echo "SERVICES_CHANGED=NO"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$2"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

cleanup() { rm -f "$RUNNER"; }

[ "$(id -un)" = "admin" ] || {
  summary_failure "wrong_linux_user" "RUN_AS_ADMIN"
  exit 1
}

cd "$ORIS" || {
  summary_failure "oris_directory_missing" "RESTORE_ORIS_REPOSITORY"
  exit 1
}

git fetch origin main >/tmp/oris-intent-pythonpath-fetch.log 2>&1 || {
  summary_failure "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
  exit 1
}

git show origin/main:scripts/dev_employee_resume_intent_boundary_repair_20260617.sh > "$RUNNER" || {
  cleanup
  summary_failure "resume_runner_materialize_failed" "RESTORE_RESUME_RUNNER"
  exit 1
}

python3 - "$RUNNER" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
replacements = {
    'EXPECTED=("$LOG_A" "$LOG_B" "$SOURCE" "$TEST_FILE")':
        'EXPECTED=("$SOURCE" "$TEST_FILE")',
    'PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest -v \\\n':
        'PYTHONPATH="$ORIS:$ORIS/scripts" PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest -v \\\n',
    'PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 - <<\'PY\' >> "$RUN_LOG" 2>&1':
        'PYTHONPATH="$ORIS:$ORIS/scripts" PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 - <<\'PY\' >> "$RUN_LOG" 2>&1',
}
for old, new in replacements.items():
    count = text.count(old)
    if count != 1:
        raise SystemExit("replacement anchor count=%d for %r" % (count, old[:80]))
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
PY
if [ "$?" -ne 0 ]; then
  cleanup
  summary_failure "resume_runner_patch_failed" "FIX_PYTHONPATH_WRAPPER"
  exit 1
fi

bash -n "$RUNNER" >/tmp/oris-intent-pythonpath-syntax.log 2>&1 || {
  cat /tmp/oris-intent-pythonpath-syntax.log
  cleanup
  summary_failure "resume_runner_syntax_failed" "FIX_RESUME_RUNNER"
  exit 1
}

bash "$RUNNER"
RC="$?"
cleanup
exit "$RC"
