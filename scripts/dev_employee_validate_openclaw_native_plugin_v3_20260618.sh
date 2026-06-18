#!/usr/bin/env bash

TASK_ID="commercial-openclaw-native-plugin-validation-20260618"
ORIS_REPO="/home/admin/projects/oris"
PLUGIN_REL="orchestration/openclaw_plugins/oris-dev-employee"
BASE_VALIDATOR_REL="scripts/dev_employee_validate_openclaw_native_plugin_20260618.sh"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-plugin-validation-v3-${STAMP}-XXXXXX)"
PATCHED_VALIDATOR="$TMP_ROOT/dev_employee_validate_openclaw_native_plugin_patched.sh"

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
  echo "VALIDATION_COMPLETE=NO"
  echo "VALIDATION_MODE=MIXED_PLUGIN_RUNTIME_CONTRACT"
  echo "PLUGIN_SOURCE_MATCHES_ORIGIN_MAIN=unknown"
  echo "ORIS_EXISTING_WORKTREE_PRESERVED=unknown"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "PLUGIN_INSTALLED_OR_ENABLED=NO"
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

if ! git -C "$ORIS_REPO" diff --quiet origin/main -- "$PLUGIN_REL"; then
  summary_fail "plugin_source_differs_from_origin_main" "REVIEW_LOCAL_PLUGIN_SOURCE_BEFORE_VALIDATION"
fi

PLUGIN_UNTRACKED="$(git -C "$ORIS_REPO" ls-files --others --exclude-standard -- "$PLUGIN_REL" 2>/dev/null || true)"
if [ -n "$PLUGIN_UNTRACKED" ]; then
  summary_fail "plugin_source_has_untracked_files" "REVIEW_LOCAL_PLUGIN_SOURCE_BEFORE_VALIDATION"
fi

STATUS_BEFORE_FILE="$TMP_ROOT/oris-status-before.bin"
STATUS_AFTER_FILE="$TMP_ROOT/oris-status-after.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$STATUS_BEFORE_FILE" 2>/dev/null || summary_fail "oris_status_capture_failed" "INSPECT_ORIS_REPOSITORY"
STATUS_BEFORE_SHA="$(sha256sum "$STATUS_BEFORE_FILE" | awk '{print $1}')"

if ! git -C "$ORIS_REPO" show "origin/main:$BASE_VALIDATOR_REL" > "$PATCHED_VALIDATOR" 2>/dev/null; then
  summary_fail "base_validator_not_found_on_origin_main" "PULL_ORIS_MAIN_AND_RETRY"
fi

python3 - "$PATCHED_VALIDATOR" <<'PY_PATCH'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

clean_gate = '[ -z "$ORIS_STATUS_BEFORE" ] || fail_now "oris_main_worktree_not_clean_before_validation" "PRESERVE_ORIS_MAIN_WORKTREE_BEFORE_VALIDATION"'
clean_replacement = '''if [ -z "$ORIS_STATUS_BEFORE" ]; then
  log "ORIS_MAIN_WORKTREE_DIRTY_BEFORE=NO"
else
  log "ORIS_MAIN_WORKTREE_DIRTY_BEFORE=YES"
fi'''
if clean_gate not in text:
    raise SystemExit("expected clean-worktree gate not found")
text = text.replace(clean_gate, clean_replacement, 1)

simple_validate = 'if (cd "$BUILD_ROOT" && openclaw plugins validate --root . --entry ./dist/index.js) >> "$RUN_LOG" 2>&1; then'
mixed_validate = 'if (cd "$BUILD_ROOT" && npm run plugin:validate) >> "$RUN_LOG" 2>&1; then'
if simple_validate not in text:
    raise SystemExit("expected simple-tool validation command not found")
text = text.replace(simple_validate, mixed_validate, 1)
text = text.replace(
    'fail_now "openclaw_plugin_validate_failed" "REPAIR_PLUGIN_MANIFEST_OR_ENTRY"',
    'fail_now "mixed_plugin_contract_validate_failed" "REPAIR_MIXED_PLUGIN_RUNTIME_CONTRACT"',
    1,
)

path.write_text(text, encoding="utf-8")
PY_PATCH
if [ "$?" -ne 0 ]; then
  summary_fail "validator_patch_failed" "INSPECT_BASE_VALIDATOR_VERSION"
fi

chmod 700 "$PATCHED_VALIDATOR"
bash -n "$PATCHED_VALIDATOR" >/dev/null 2>&1 || summary_fail "patched_validator_syntax_failed" "INSPECT_VALIDATOR_PATCH"

bash "$PATCHED_VALIDATOR"
INNER_RC="$?"

git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$STATUS_AFTER_FILE" 2>/dev/null || summary_fail "oris_status_recapture_failed" "INSPECT_ORIS_REPOSITORY"
STATUS_AFTER_SHA="$(sha256sum "$STATUS_AFTER_FILE" | awk '{print $1}')"

if [ "$STATUS_BEFORE_SHA" != "$STATUS_AFTER_SHA" ]; then
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=oris_existing_worktree_changed_during_validation"
  echo "VALIDATION_COMPLETE=NO"
  echo "VALIDATION_MODE=MIXED_PLUGIN_RUNTIME_CONTRACT"
  echo "PLUGIN_SOURCE_MATCHES_ORIGIN_MAIN=YES"
  echo "ORIS_EXISTING_WORKTREE_PRESERVED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "PLUGIN_INSTALLED_OR_ENABLED=NO"
  echo "NEXT_ACTION=INSPECT_UNEXPECTED_ORIS_WORKTREE_CHANGE"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit 1
fi

exit "$INNER_RC"
