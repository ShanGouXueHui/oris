#!/usr/bin/env bash

TASK_ID="commercial-openclaw-native-plugin-install-20260618"
ORIS_REPO="/home/admin/projects/oris"
BASE_ROLLBACK_REL="scripts/dev_employee_rollback_openclaw_native_plugin_20260618.sh"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-plugin-rollback-v2-${STAMP}-XXXXXX)"
PATCHED_ROLLBACK="$TMP_ROOT/dev_employee_rollback_openclaw_native_plugin_patched.sh"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

summary_fail() {
  local code="$1"
  local action="$2"
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$code"
  echo "ROLLBACK_VERSION=V2_NON_INTERACTIVE"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=$action"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit 1
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  summary_fail "wrong_linux_user" "RUN_AS_ADMIN"
fi

for cmd in git python3 bash; do
  command -v "$cmd" >/dev/null 2>&1 || summary_fail "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done

[ -d "$ORIS_REPO/.git" ] || summary_fail "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"

git -C "$ORIS_REPO" fetch origin main >/dev/null 2>&1 || summary_fail "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"

if ! git -C "$ORIS_REPO" show "origin/main:$BASE_ROLLBACK_REL" > "$PATCHED_ROLLBACK" 2>/dev/null; then
  summary_fail "base_rollback_not_found_on_origin_main" "PULL_ORIS_MAIN_AND_RETRY"
fi

python3 - "$PATCHED_ROLLBACK" <<'PY_PATCH'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = 'openclaw plugins uninstall "$PLUGIN_ID" >> "$RUN_LOG" 2>&1'
new = 'openclaw plugins uninstall "$PLUGIN_ID" --force >> "$RUN_LOG" 2>&1'
if old not in text:
    raise SystemExit("interactive uninstall command not found")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
PY_PATCH
if [ "$?" -ne 0 ]; then
  summary_fail "rollback_patch_failed" "INSPECT_BASE_ROLLBACK_VERSION"
fi

chmod 700 "$PATCHED_ROLLBACK"
bash -n "$PATCHED_ROLLBACK" >/dev/null 2>&1 || summary_fail "patched_rollback_syntax_failed" "INSPECT_ROLLBACK_PATCH"

bash "$PATCHED_ROLLBACK"
exit "$?"
