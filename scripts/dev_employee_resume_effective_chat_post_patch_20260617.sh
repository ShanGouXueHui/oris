#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
STAMP="$(date +%Y%m%d%H%M%S)"
RUNNER="/tmp/oris-effective-chat-post-runner-$STAMP.sh"

summary_failure() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=resume-effective-chat-post-patch-20260617"
  echo "FAILURE_CODE=$1"
  echo "NGINX_CHANGED=NO"
  echo "SERVICES_CHANGED=NO"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$2"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

cleanup() {
  rm -f "$RUNNER"
}

[ "$(id -un)" = "admin" ] || {
  summary_failure "wrong_linux_user" "RUN_AS_ADMIN"
  exit 1
}

cd "$ORIS" || {
  summary_failure "oris_directory_missing" "RESTORE_ORIS_REPOSITORY"
  exit 1
}

git fetch origin main >/tmp/oris-effective-chat-post-resume-fetch.log 2>&1 || {
  summary_failure "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
  exit 1
}

git show origin/main:scripts/dev_employee_patch_effective_chat_post_route_20260617.sh > "$RUNNER" || {
  cleanup
  summary_failure "patch_runner_materialize_failed" "RESTORE_PATCH_RUNNER"
  exit 1
}

python3 - "$RUNNER" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = "indent=matches[0].group(2)"
new = "indent=matches[0].group(1)"
if text.count(old) != 1:
    raise SystemExit("capture-group anchor count=%s" % text.count(old))
path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY
if [ "$?" -ne 0 ]; then
  cleanup
  summary_failure "patch_runner_capture_fix_failed" "FIX_PATCH_RUNNER"
  exit 1
fi

bash -n "$RUNNER" >/tmp/oris-effective-chat-post-resume-syntax.log 2>&1 || {
  cat /tmp/oris-effective-chat-post-resume-syntax.log
  cleanup
  summary_failure "patch_runner_syntax_failed" "FIX_PATCH_RUNNER"
  exit 1
}

bash "$RUNNER"
RC="$?"
cleanup
exit "$RC"
