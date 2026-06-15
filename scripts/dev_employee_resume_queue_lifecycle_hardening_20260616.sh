#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
BASE="$ORIS/scripts/dev_employee_deploy_queue_lifecycle_hardening_v2_20260616.sh"
TMP="/tmp/oris-deploy-queue-lifecycle-resume-$$.sh"

failure_summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=commercial-hardening-queue-lifecycle-20260616"
  echo "FAILURE_CODE=$1"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "BROWSER_TEST_PERFORMED=NO"
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

git fetch origin main >/tmp/oris-queue-lifecycle-resume-fetch.log 2>&1
if [ "$?" -ne 0 ]; then
  failure_summary "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
  exit 1
fi

git rebase origin/main >/tmp/oris-queue-lifecycle-resume-rebase.log 2>&1
if [ "$?" -ne 0 ]; then
  failure_summary "oris_rebase_failed" "INSPECT_ORIS_REBASE"
  exit 1
fi

if [ ! -f "$BASE" ]; then
  failure_summary "deployment_script_missing" "RESTORE_DEPLOYMENT_SCRIPT"
  exit 1
fi

cp "$BASE" "$TMP"
if [ "$?" -ne 0 ]; then
  failure_summary "deployment_script_copy_failed" "INSPECT_TMP_DIRECTORY"
  exit 1
fi

python3 - "$TMP" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = '''journalctl --user -u "$BRIDGE_SERVICE" -n 80 --no-pager > /tmp/oris-queue-lifecycle-bridge-journal-$STAMP.log 2>&1 || true
grep -q 'WORKER_SLOT_ACQUIRED' /tmp/oris-queue-lifecycle-bridge-journal-$STAMP.log
[ "$?" -eq 0 ] || fail "bridge_worker_slot_not_observed" "INSPECT_BRIDGE_V3_JOURNAL"
BRIDGE_WORKER_SLOT="PASS"
'''
new = '''SLOT_FILE="$ORIS/run/dev_employee_worker_slots/slot-0.lock"
SLOT_READY="NO"
for _attempt in 1 2 3 4 5 6 7 8 9 10; do
  if [ -s "$SLOT_FILE" ]; then
    SLOT_READY="YES"
    break
  fi
  sleep 1
done
[ "$SLOT_READY" = "YES" ] || fail "bridge_worker_slot_not_observed" "INSPECT_BRIDGE_V3_SLOT_FILE"
python3 - "$SLOT_FILE" <<'PY_SLOT' >> "$RUN_LOG" 2>&1
import json
import os
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload.get("slot") == 0
assert payload.get("max_concurrency") == 1
pid = int(payload.get("worker_pid") or 0)
assert pid > 0
os.kill(pid, 0)
assert payload.get("worker_id")
PY_SLOT
[ "$?" -eq 0 ] || fail "bridge_worker_slot_invalid" "INSPECT_BRIDGE_V3_SLOT_FILE"
BRIDGE_WORKER_SLOT="PASS"
'''
if old not in text:
    raise SystemExit("worker-slot validation patch anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY
if [ "$?" -ne 0 ]; then
  rm -f "$TMP"
  failure_summary "resume_patch_failed" "FIX_RESUME_SCRIPT"
  exit 1
fi

bash -n "$TMP"
if [ "$?" -ne 0 ]; then
  rm -f "$TMP"
  failure_summary "patched_deployment_syntax_failed" "FIX_RESUME_SCRIPT"
  exit 1
fi

bash "$TMP"
RC="$?"
rm -f "$TMP"
exit "$RC"
