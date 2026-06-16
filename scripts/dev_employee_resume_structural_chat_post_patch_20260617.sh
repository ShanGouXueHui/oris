#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
STAMP="$(date +%Y%m%d%H%M%S)"
RUNNER="/tmp/oris-effective-chat-runner-$STAMP.sh"
PATCHER="/tmp/oris-nginx-chat-patcher-$STAMP.py"

summary_failure() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=resume-structural-chat-post-patch-20260617"
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
  rm -f "$RUNNER" "$PATCHER"
}

[ "$(id -un)" = "admin" ] || {
  summary_failure "wrong_linux_user" "RUN_AS_ADMIN"
  exit 1
}

cd "$ORIS" || {
  summary_failure "oris_directory_missing" "RESTORE_ORIS_REPOSITORY"
  exit 1
}

git fetch origin main >/tmp/oris-structural-chat-fetch.log 2>&1 || {
  summary_failure "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
  exit 1
}

git show origin/main:scripts/dev_employee_patch_effective_chat_post_route_20260617.sh > "$RUNNER" || {
  cleanup
  summary_failure "deployment_runner_materialize_failed" "RESTORE_DEPLOYMENT_RUNNER"
  exit 1
}

git show origin/main:scripts/dev_employee_patch_nginx_chat_route.py > "$PATCHER" || {
  cleanup
  summary_failure "structural_patcher_materialize_failed" "RESTORE_STRUCTURAL_PATCHER"
  exit 1
}

PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$PATCHER" --self-test >/tmp/oris-structural-chat-self-test.log 2>&1 || {
  cat /tmp/oris-structural-chat-self-test.log
  cleanup
  summary_failure "structural_patcher_self_test_failed" "FIX_STRUCTURAL_PATCHER"
  exit 1
}

/usr/bin/python3 - "$RUNNER" "$PATCHER" <<'PY'
from pathlib import Path
import sys

runner = Path(sys.argv[1])
patcher = Path(sys.argv[2])
text = runner.read_text(encoding="utf-8")
start_marker = 'python3 - "$CONFIG" "$PATCHED" "$PATCH_AUDIT" <<\'PY\' >> "$RUN_LOG" 2>&1\n'
end_marker = '\nPY\n[ "$?" -eq 0 ] || fail "effective_config_patch_generation_failed" "INSPECT_EFFECTIVE_NGINX_CONFIG"'
start = text.find(start_marker)
if start < 0:
    raise SystemExit("inline patch start marker missing")
end = text.find(end_marker, start + len(start_marker))
if end < 0:
    raise SystemExit("inline patch end marker missing")
replacement = (
    'PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "'
    + str(patcher)
    + '" --input "$CONFIG" --output "$PATCHED" --audit "$PATCH_AUDIT" >> "$RUN_LOG" 2>&1'
)
text = text[:start] + replacement + text[end + len('\nPY'):]
old = "assert p['effective_guard_replaced']"
new = "assert p['effective_guard_present']"
if text.count(old) != 1:
    raise SystemExit("audit compatibility anchor count=%s" % text.count(old))
text = text.replace(old, new, 1)
runner.write_text(text, encoding="utf-8")
PY
if [ "$?" -ne 0 ]; then
  cleanup
  summary_failure "deployment_runner_patch_failed" "FIX_STRUCTURAL_PATCH_WRAPPER"
  exit 1
fi

bash -n "$RUNNER" >/tmp/oris-structural-chat-runner-syntax.log 2>&1 || {
  cat /tmp/oris-structural-chat-runner-syntax.log
  cleanup
  summary_failure "deployment_runner_syntax_failed" "FIX_DEPLOYMENT_RUNNER"
  exit 1
}

bash "$RUNNER"
RC="$?"
cleanup
exit "$RC"
