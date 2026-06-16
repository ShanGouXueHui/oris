#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
TASK_ID="diagnose-structural-nginx-patcher-20260617"
STAMP="$(date +%Y%m%d%H%M%S)"
CONFIG="/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf"
PATCHER="/tmp/oris-nginx-patcher-$STAMP.py"
DIAG="/tmp/oris-nginx-patcher-diag-$STAMP.py"
LOG_DIR="$ORIS/logs/dev_employee/conversational_web"
RUN_LOG="$LOG_DIR/nginx-patcher-diagnostic-$STAMP.log"
RESULT_JSON="$LOG_DIR/nginx-patcher-diagnostic-$STAMP.json"
LOG_COMMIT=""

mkdir -p "$LOG_DIR"
: > "$RUN_LOG"

summary_failure() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$1"
  echo "NGINX_CHANGED=NO"
  echo "SERVICES_CHANGED=NO"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$2"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

cleanup() { rm -f "$PATCHER" "$DIAG"; }

[ "$(id -un)" = "admin" ] || { summary_failure "wrong_linux_user" "RUN_AS_ADMIN"; exit 1; }
cd "$ORIS" || { summary_failure "oris_directory_missing" "RESTORE_ORIS_REPOSITORY"; exit 1; }

git fetch origin main >> "$RUN_LOG" 2>&1 || { summary_failure "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"; exit 1; }
git restore --source=origin/main --staged --worktree -- . >> "$RUN_LOG" 2>&1 || { summary_failure "tracked_worktree_sync_failed" "INSPECT_ORIS_GIT_STATE"; exit 1; }
git reset --mixed origin/main >> "$RUN_LOG" 2>&1 || { summary_failure "local_branch_sync_failed" "INSPECT_ORIS_GIT_STATE"; exit 1; }

git show origin/main:scripts/dev_employee_patch_nginx_chat_route.py > "$PATCHER" || { cleanup; summary_failure "patcher_materialize_failed" "RESTORE_STRUCTURAL_PATCHER"; exit 1; }
git show origin/main:scripts/dev_employee_diagnose_nginx_patcher.py > "$DIAG" || { cleanup; summary_failure "diagnostic_materialize_failed" "RESTORE_DIAGNOSTIC"; exit 1; }

PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$PATCHER" --self-test >> "$RUN_LOG" 2>&1 || { cleanup; summary_failure "patcher_self_test_failed" "FIX_STRUCTURAL_PATCHER"; exit 1; }
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$DIAG" --patcher "$PATCHER" --config "$CONFIG" --output "$RESULT_JSON" >> "$RUN_LOG" 2>&1 || { cleanup; summary_failure "real_config_diagnostic_failed" "FIX_DIAGNOSTIC"; exit 1; }

read_json() { python3 -c "import json;print(json.load(open('$RESULT_JSON'))[$1])"; }
SERVER_BLOCK_COUNT="$(read_json "'server_block_count'")"
HTTPS_MATCH_COUNT="$(read_json "'https_match_count'")"
IF_BLOCK_COUNT="$(read_json "'if_block_count'")"
METHOD_GUARD_COUNT="$(read_json "'method_guard_count'")"
PATCH_ATTEMPT="$(read_json "'patch_result'")"
PATCH_ERROR_TYPE="$(read_json "'patch_error_type'")"
PATCH_ERROR_MESSAGE="$(read_json "'patch_error_message'")"
MAP_MARKER_PRESENT="$(python3 -c "import json;print('YES' if json.load(open('$RESULT_JSON'))['map_marker_present'] else 'NO')")"
CHAT_LOCATION_PRESENT="$(python3 -c "import json;print('YES' if json.load(open('$RESULT_JSON'))['chat_location_present'] else 'NO')")"

git add -- "${RUN_LOG#$ORIS/}" "${RESULT_JSON#$ORIS/}" >/tmp/oris-nginx-diag-add-$STAMP.log 2>&1 || { cleanup; summary_failure "diagnostic_log_add_failed" "INSPECT_ORIS_GIT_STATE"; exit 1; }
git commit --only -m "chore(dev-employee): record Nginx patcher diagnostic $STAMP" -- "${RUN_LOG#$ORIS/}" "${RESULT_JSON#$ORIS/}" >/tmp/oris-nginx-diag-commit-$STAMP.log 2>&1 || { cleanup; summary_failure "diagnostic_log_commit_failed" "INSPECT_ORIS_GIT_STATE"; exit 1; }
git push origin main >/tmp/oris-nginx-diag-push-$STAMP.log 2>&1 || { cleanup; summary_failure "diagnostic_log_push_failed" "RESOLVE_GITHUB_PUSH"; exit 1; }
LOG_COMMIT="$(git rev-parse HEAD)"
cleanup

echo
echo "===== SUMMARY ====="
echo "RESULT=PASS"
echo "TASK_ID=$TASK_ID"
echo "SELF_TEST=PASS"
echo "REAL_CONFIG_ANALYSIS=PASS"
echo "PATCH_ATTEMPT=$PATCH_ATTEMPT"
echo "SERVER_BLOCK_COUNT=$SERVER_BLOCK_COUNT"
echo "HTTPS_MATCH_COUNT=$HTTPS_MATCH_COUNT"
echo "IF_BLOCK_COUNT=$IF_BLOCK_COUNT"
echo "METHOD_GUARD_COUNT=$METHOD_GUARD_COUNT"
echo "MAP_MARKER_PRESENT=$MAP_MARKER_PRESENT"
echo "CHAT_LOCATION_PRESENT=$CHAT_LOCATION_PRESENT"
echo "PATCH_ERROR_TYPE=$PATCH_ERROR_TYPE"
echo "PATCH_ERROR_MESSAGE=$PATCH_ERROR_MESSAGE"
echo "NGINX_CHANGED=NO"
echo "SERVICES_CHANGED=NO"
echo "FAILURE_CODE="
echo "LOG_COMMIT=$LOG_COMMIT"
echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
echo "REAL_PRODUCT_CHANGE=NO"
echo "NEXT_ACTION=FIX_PATCHER_FROM_DIAGNOSTIC"
echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
echo "===== END SUMMARY ====="
