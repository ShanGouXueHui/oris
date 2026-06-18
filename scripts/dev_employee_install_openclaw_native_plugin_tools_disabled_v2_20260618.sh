#!/usr/bin/env bash

TASK_ID="commercial-openclaw-native-plugin-install-20260618"
ORIS_REPO="/home/admin/projects/oris"
BASE_INSTALLER_REL="scripts/dev_employee_install_openclaw_native_plugin_tools_disabled_20260618.sh"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-plugin-install-v2-${STAMP}-XXXXXX)"
PATCHED_INSTALLER="$TMP_ROOT/dev_employee_install_openclaw_native_plugin_tools_disabled_patched.sh"

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
  echo "INSTALLER_VERSION=V2_TYPED_HOOK_AWARE"
  echo "PLUGIN_INSTALLED_OR_ENABLED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=$action"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit 1
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  summary_fail "wrong_linux_user" "RUN_AS_ADMIN"
fi

for cmd in git python3 bash sha256sum; do
  command -v "$cmd" >/dev/null 2>&1 || summary_fail "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done

[ -d "$ORIS_REPO/.git" ] || summary_fail "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"

git -C "$ORIS_REPO" fetch origin main >/dev/null 2>&1 || summary_fail "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"

STATUS_BEFORE_FILE="$TMP_ROOT/oris-status-before.bin"
STATUS_AFTER_FILE="$TMP_ROOT/oris-status-after.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$STATUS_BEFORE_FILE" 2>/dev/null || summary_fail "oris_status_capture_failed" "INSPECT_ORIS_REPOSITORY"
STATUS_BEFORE_SHA="$(sha256sum "$STATUS_BEFORE_FILE" | awk '{print $1}')"

if ! git -C "$ORIS_REPO" show "origin/main:$BASE_INSTALLER_REL" > "$PATCHED_INSTALLER" 2>/dev/null; then
  summary_fail "base_installer_not_found_on_origin_main" "PULL_ORIS_MAIN_AND_RETRY"
fi

python3 - "$PATCHED_INSTALLER" <<'PY_PATCH'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

old_uninstall = 'openclaw plugins uninstall "$PLUGIN_ID" >> "$RUN_LOG" 2>&1 || true'
new_uninstall = 'openclaw plugins uninstall "$PLUGIN_ID" --force >> "$RUN_LOG" 2>&1 || true'
if old_uninstall not in text:
    raise SystemExit("automatic rollback uninstall command not found")
text = text.replace(old_uninstall, new_uninstall, 1)

old_hook_parser = "elif low in {'hooks','registeredhooks','hooknames'}: add(x,hooks)"
new_hook_parser = "elif low in {'hooks','registeredhooks','hooknames','typedhooks','customhooks'}: add(x,hooks)"
if old_hook_parser not in text:
    raise SystemExit("runtime hook parser not found")
text = text.replace(old_hook_parser, new_hook_parser, 1)

path.write_text(text, encoding="utf-8")
PY_PATCH
if [ "$?" -ne 0 ]; then
  summary_fail "installer_patch_failed" "INSPECT_BASE_INSTALLER_VERSION"
fi

chmod 700 "$PATCHED_INSTALLER"
bash -n "$PATCHED_INSTALLER" >/dev/null 2>&1 || summary_fail "patched_installer_syntax_failed" "INSPECT_INSTALLER_PATCH"

bash "$PATCHED_INSTALLER"
INNER_RC="$?"

git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$STATUS_AFTER_FILE" 2>/dev/null || summary_fail "oris_status_recapture_failed" "INSPECT_ORIS_REPOSITORY"
STATUS_AFTER_SHA="$(sha256sum "$STATUS_AFTER_FILE" | awk '{print $1}')"

if [ "$STATUS_BEFORE_SHA" != "$STATUS_AFTER_SHA" ]; then
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=oris_existing_worktree_changed_during_install_wrapper"
  echo "INSTALLER_VERSION=V2_TYPED_HOOK_AWARE"
  echo "ORIS_EXISTING_WORKTREE_PRESERVED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=INSPECT_UNEXPECTED_ORIS_WORKTREE_CHANGE"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit 1
fi

exit "$INNER_RC"
