#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
SOURCE="$ORIS_REPO/scripts/dev_employee_native_openclaw_browser_acceptance_20260617.sh"
TMP_SCRIPT="$(mktemp /tmp/oris-native-openclaw-browser-acceptance-run-XXXXXX.sh)"

cleanup() {
  rm -f "$TMP_SCRIPT"
}
trap cleanup EXIT

summary_failed() {
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$1"
  echo "CURRENT_TASK_UPDATED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "PRODUCT_REPOSITORY_MUTATED=NO"
  echo "NEXT_ACTION=$2"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  summary_failed "wrong_linux_user" "RUN_AS_ADMIN"
  exit 1
fi

if [ ! -f "$SOURCE" ]; then
  summary_failed "acceptance_source_missing" "PULL_ORIS_MAIN_AND_RETRY"
  exit 1
fi

python3 - "$SOURCE" "$TMP_SCRIPT" <<'PY'
import os
import sys
from pathlib import Path

source=Path(sys.argv[1])
target=Path(sys.argv[2])
text=source.read_text(encoding="utf-8")
old_prompt="""    printf '\\n[%s]\\n%s\\n输入 y 表示通过，n 表示失败：' \"$key\" \"$prompt\"
"""
new_prompt="""    printf '\\n[%s]\\n%s\\n输入 y 表示通过，n 表示失败：' \"$key\" \"$prompt\" >&2
"""
old_invalid='''        echo "只输入 y 或 n。"
'''
new_invalid='''        echo "只输入 y 或 n。" >&2
'''
if old_prompt not in text or old_invalid not in text:
    print("expected interaction block not found",file=sys.stderr)
    raise SystemExit(2)
text=text.replace(old_prompt,new_prompt,1).replace(old_invalid,new_invalid,1)
target.write_text(text,encoding="utf-8")
os.chmod(target,0o700)
PY
if [ "$?" -ne 0 ]; then
  summary_failed "temporary_interaction_patch_failed" "INSPECT_ACCEPTANCE_SCRIPT_VERSION"
  exit 1
fi

if ! bash -n "$TMP_SCRIPT" >/dev/null 2>&1; then
  summary_failed "patched_acceptance_script_syntax_invalid" "REPAIR_ACCEPTANCE_SCRIPT"
  exit 1
fi

bash "$TMP_SCRIPT"
exit "$?"
