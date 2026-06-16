#!/usr/bin/env bash
ORIS="/home/admin/projects/oris"
STAMP="$(date +%Y%m%d%H%M%S)"
SOURCE="scripts/dev_employee_openclaw_provider.py"
TEST="tests/test_dev_employee_openclaw_provider.py"
ARCHIVE="$HOME/.local/state/oris/intent_boundary_recovery/log-cleanup-$STAMP"
NEXT="/tmp/oris-intent-pythonpath-$STAMP.sh"

fail() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=resume-intent-after-log-cleanup-20260617"
  echo "FAILURE_CODE=$1"
  echo "SERVICES_CHANGED=NO"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$2"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit 1
}

[ "$(id -un)" = "admin" ] || fail wrong_linux_user RUN_AS_ADMIN
cd "$ORIS" || fail oris_directory_missing RESTORE_ORIS_REPOSITORY
git fetch origin main >/tmp/oris-intent-clean-fetch.log 2>&1 || fail oris_fetch_failed RESOLVE_ORIS_GIT_FETCH

mapfile -t DIRTY < <({ git diff --name-only; git diff --cached --name-only; } | sed '/^$/d' | sort -u)
printf '%s\n' "${DIRTY[@]}" | grep -Fxq "$SOURCE" || fail provider_patch_missing RESTORE_PROVIDER_PATCH
printf '%s\n' "${DIRTY[@]}" | grep -Fxq "$TEST" || fail provider_test_patch_missing RESTORE_PROVIDER_TEST_PATCH

mkdir -p "$ARCHIVE"
chmod 700 "$ARCHIVE"
LOG_COUNT=0
for path in "${DIRTY[@]}"; do
  [ "$path" = "$SOURCE" ] && continue
  [ "$path" = "$TEST" ] && continue
  case "$path" in
    logs/dev_employee/conversational_web/*intent-boundar*.log|logs/dev_employee/conversational_web/*intent-boundar*.json)
      mkdir -p "$ARCHIVE/$(dirname "$path")"
      cp -p "$path" "$ARCHIVE/$path" || fail log_archive_failed INSPECT_PRIVATE_ARCHIVE
      git restore --source=origin/main --staged --worktree -- "$path" || fail log_restore_failed INSPECT_ORIS_GIT_STATE
      LOG_COUNT=$((LOG_COUNT + 1))
      ;;
    *) fail unexpected_non_log_tracked_drift MANUAL_REVIEW_REQUIRED ;;
  esac
done

mapfile -t AFTER < <({ git diff --name-only; git diff --cached --name-only; } | sed '/^$/d' | sort -u)
[ "${#AFTER[@]}" -eq 2 ] || fail post_cleanup_change_count_unexpected INSPECT_ORIS_GIT_STATE
printf '%s\n' "${AFTER[@]}" | grep -Fxq "$SOURCE" || fail provider_patch_lost RESTORE_PROVIDER_PATCH
printf '%s\n' "${AFTER[@]}" | grep -Fxq "$TEST" || fail provider_test_patch_lost RESTORE_PROVIDER_TEST_PATCH

git show origin/main:scripts/dev_employee_resume_intent_boundary_with_pythonpath_20260617.sh > "$NEXT" || fail wrapper_materialize_failed RESTORE_PYTHONPATH_WRAPPER
bash "$NEXT"
RC="$?"
rm -f "$NEXT"
exit "$RC"
