#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
PRODUCT="/home/admin/projects/oris-final-acceptance-api"
SOURCE="scripts/dev_employee_openclaw_provider.py"
TEST_FILE="tests/test_dev_employee_openclaw_provider.py"
TASK_ID="finalize-conversational-intent-boundary-repair-20260617"
STAMP="$(date +%Y%m%d%H%M%S)"
ARCHIVE="$HOME/.local/state/oris/intent_boundary_recovery/final-$STAMP"
PATCH="$ARCHIVE/provider-test.patch"
TMP="$HOME/.local/state/oris/tmp/intent-final-$STAMP"
RUN_LOG="$TMP/run.log"
EVIDENCE="$TMP/evidence.json"
EVIDENCE_WT="$TMP/evidence-worktree"

RESULT="FAILED"
DIRTY_SCOPE_GUARD="NOT_RUN"
PRIVATE_ARCHIVE="NOT_RUN"
TRACKED_SYNC="NOT_RUN"
PATCH_REAPPLY="NOT_RUN"
STATIC_CHECKS="NOT_RUN"
TEST_RESULT="NOT_RUN"
REGRESSION_MESSAGE="NOT_RUN"
CONTROL_COMMANDS="NOT_RUN"
NEGATED_SECRET_POLICY="NOT_RUN"
ACTIVE_QUEUE_GATE="NOT_RUN"
CODE_COMMIT=""
CODE_PUSH="NOT_RUN"
SERVICE_RESTART="NOT_RUN"
WEB_HEALTH="NOT_RUN"
PRODUCT_SHA_UNCHANGED="NOT_VERIFIED"
PRODUCT_WORKTREE_CLEAN="NOT_VERIFIED"
FINAL_WORKTREE_CLEAN="NOT_VERIFIED"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_FINAL_INTENT_REPAIR"

mkdir -p "$ARCHIVE" "$TMP"
chmod 700 "$ARCHIVE" "$TMP"
: > "$RUN_LOG"

service_state() { systemctl --user is-active "$1" 2>/dev/null || true; }
log() { printf '%s\n' "$*" >> "$RUN_LOG"; }

write_evidence() {
  python3 - "$EVIDENCE" <<PY
import json
p={
"task_id":"$TASK_ID","checked_at":"$(date -Is)","result":"$RESULT","failure_code":"$FAILURE_CODE" or None,
"dirty_scope_guard":"$DIRTY_SCOPE_GUARD","private_archive":"$PRIVATE_ARCHIVE","archive_path":"$ARCHIVE",
"tracked_sync":"$TRACKED_SYNC","patch_reapply":"$PATCH_REAPPLY","static_checks":"$STATIC_CHECKS",
"test_runner":"unittest","test_result":"$TEST_RESULT","regression_message":"$REGRESSION_MESSAGE",
"control_commands":"$CONTROL_COMMANDS","negated_secret_policy":"$NEGATED_SECRET_POLICY",
"active_queue_gate":"$ACTIVE_QUEUE_GATE","code_commit":"$CODE_COMMIT" or None,"code_push":"$CODE_PUSH",
"service_restart":"$SERVICE_RESTART","web_health":"$WEB_HEALTH",
"product_sha_unchanged":"$PRODUCT_SHA_UNCHANGED","product_worktree_clean":"$PRODUCT_WORKTREE_CLEAN",
"final_worktree_clean":"$FINAL_WORKTREE_CLEAN",
"services":{"openclaw":"$(service_state openclaw-gateway.service)","bridge":"$(service_state oris-dev-employee-bridge.service)","intake":"$(service_state oris-dev-employee-intake.service)","web":"$(service_state oris-dev-employee-web-console.service)"},
"real_product_task_submitted":False,"real_product_change":False,"next_action":"$NEXT_ACTION"}
open("$EVIDENCE","w",encoding="utf-8").write(json.dumps(p,ensure_ascii=False,indent=2)+"\n")
PY
}

commit_evidence() {
  git fetch origin main >/dev/null 2>&1 || return 1
  git worktree add --detach "$EVIDENCE_WT" origin/main >/dev/null 2>&1 || return 1
  mkdir -p "$EVIDENCE_WT/logs/dev_employee/conversational_web"
  cp "$RUN_LOG" "$EVIDENCE_WT/logs/dev_employee/conversational_web/finalize-intent-boundary-$STAMP.log" || return 1
  cp "$EVIDENCE" "$EVIDENCE_WT/logs/dev_employee/conversational_web/finalize-intent-boundary-$STAMP.json" || return 1
  (
    cd "$EVIDENCE_WT" || exit 1
    git add -f -- logs/dev_employee/conversational_web/finalize-intent-boundary-$STAMP.log logs/dev_employee/conversational_web/finalize-intent-boundary-$STAMP.json || exit 1
    git commit -m "test(dev-employee): verify final intent boundary repair $STAMP" || exit 1
    git push origin HEAD:main || exit 1
    git rev-parse HEAD
  ) > "$TMP/evidence-git.log" 2>&1
  local rc="$?"
  [ "$rc" -eq 0 ] && LOG_COMMIT="$(tail -n 1 "$TMP/evidence-git.log")"
  git worktree remove --force "$EVIDENCE_WT" >/dev/null 2>&1 || true
  return "$rc"
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "DIRTY_SCOPE_GUARD=$DIRTY_SCOPE_GUARD"
  echo "PRIVATE_ARCHIVE=$PRIVATE_ARCHIVE"
  echo "TRACKED_SYNC=$TRACKED_SYNC"
  echo "PATCH_REAPPLY=$PATCH_REAPPLY"
  echo "STATIC_CHECKS=$STATIC_CHECKS"
  echo "TEST_RUNNER=unittest"
  echo "TEST_RESULT=$TEST_RESULT"
  echo "REGRESSION_MESSAGE=$REGRESSION_MESSAGE"
  echo "CONTROL_COMMANDS=$CONTROL_COMMANDS"
  echo "NEGATED_SECRET_POLICY=$NEGATED_SECRET_POLICY"
  echo "ACTIVE_QUEUE_GATE=$ACTIVE_QUEUE_GATE"
  echo "CODE_COMMIT=$CODE_COMMIT"
  echo "CODE_PUSH=$CODE_PUSH"
  echo "SERVICE_RESTART=$SERVICE_RESTART"
  echo "WEB_HEALTH=$WEB_HEALTH"
  echo "PRODUCT_SHA_UNCHANGED=$PRODUCT_SHA_UNCHANGED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "FINAL_WORKTREE_CLEAN=$FINAL_WORKTREE_CLEAN"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "OPENCLAW_SERVICE=$(service_state openclaw-gateway.service)"
  echo "BRIDGE_SERVICE=$(service_state oris-dev-employee-bridge.service)"
  echo "INTAKE_SERVICE=$(service_state oris-dev-employee-intake.service)"
  echo "WEB_CONSOLE_SERVICE=$(service_state oris-dev-employee-web-console.service)"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"; NEXT_ACTION="$2"; RESULT="FAILED"
  log "FAILURE_CODE=$FAILURE_CODE"
  write_evidence
  [ "$CODE_PUSH" = "PASS" ] && commit_evidence || true
  summary
  git worktree remove --force "$EVIDENCE_WT" >/dev/null 2>&1 || true
  exit 1
}

[ "$(id -un)" = "admin" ] || { FAILURE_CODE="wrong_linux_user"; NEXT_ACTION="RUN_AS_ADMIN"; write_evidence; summary; exit 1; }
cd "$ORIS" || { FAILURE_CODE="oris_directory_missing"; NEXT_ACTION="RESTORE_ORIS_REPOSITORY"; write_evidence; summary; exit 1; }

git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
BASE_PRODUCT_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
BASE_PRODUCT_REMOTE="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n1)"
[ -n "$BASE_PRODUCT_SHA" ] && [ "$BASE_PRODUCT_SHA" = "$BASE_PRODUCT_REMOTE" ] || fail "product_baseline_mismatch" "INSPECT_PRODUCT_REPOSITORY"
[ -z "$(git -C "$PRODUCT" status --porcelain --untracked-files=no)" ] || fail "product_baseline_dirty" "INSPECT_PRODUCT_REPOSITORY"

ACTIVE_COUNT="$(find orchestration/dev_employee_queue -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' \) 2>/dev/null | wc -l | tr -d ' ')"
[ "$ACTIVE_COUNT" = "0" ] || fail "active_queue_not_empty" "INSPECT_ACTIVE_TASKS"
ACTIVE_QUEUE_GATE="PASS"

mapfile -t DIRTY < <({ git diff --name-only; git diff --cached --name-only; } | sed '/^$/d' | sort -u)
printf '%s\n' "${DIRTY[@]}" | grep -Fxq "$SOURCE" || fail "provider_patch_missing" "RESTORE_PROVIDER_PATCH"
printf '%s\n' "${DIRTY[@]}" | grep -Fxq "$TEST_FILE" || fail "provider_test_patch_missing" "RESTORE_PROVIDER_TEST_PATCH"
for path in "${DIRTY[@]}"; do
  [ "$path" = "$SOURCE" ] && continue
  [ "$path" = "$TEST_FILE" ] && continue
  case "$path" in
    logs/dev_employee/conversational_web/*intent*.log|logs/dev_employee/conversational_web/*intent*.json) ;;
    *) fail "unexpected_non_log_tracked_drift" "MANUAL_REVIEW_REQUIRED" ;;
  esac
done
DIRTY_SCOPE_GUARD="PASS"

git diff --binary > "$ARCHIVE/all-tracked.patch" || fail "full_patch_archive_failed" "INSPECT_PRIVATE_ARCHIVE"
git diff --binary origin/main -- "$SOURCE" "$TEST_FILE" > "$PATCH" || fail "code_patch_archive_failed" "INSPECT_PRIVATE_ARCHIVE"
[ -s "$PATCH" ] || fail "code_patch_empty" "RESTORE_PROVIDER_PATCH"
for path in "${DIRTY[@]}"; do
  mkdir -p "$ARCHIVE/$(dirname "$path")"
  cp -p "$path" "$ARCHIVE/$path" || fail "archive_copy_failed" "INSPECT_PRIVATE_ARCHIVE"
done
find "$ARCHIVE" -type f ! -name manifest.sha256 -print0 | sort -z | xargs -0 sha256sum > "$ARCHIVE/manifest.sha256" || fail "archive_manifest_failed" "INSPECT_PRIVATE_ARCHIVE"
chmod -R go-rwx "$ARCHIVE"
PRIVATE_ARCHIVE="PASS"

git restore --source=origin/main --staged --worktree -- . >> "$RUN_LOG" 2>&1 || fail "tracked_restore_failed" "RESTORE_FROM_PRIVATE_ARCHIVE"
git reset --mixed origin/main >> "$RUN_LOG" 2>&1 || fail "local_branch_sync_failed" "RESTORE_FROM_PRIVATE_ARCHIVE"
[ -z "$(git status --porcelain --untracked-files=no)" ] || fail "tracked_sync_not_clean" "INSPECT_ORIS_GIT_STATE"
TRACKED_SYNC="PASS"

git apply --check "$PATCH" >> "$RUN_LOG" 2>&1 || fail "code_patch_check_failed" "REVIEW_PRIVATE_ARCHIVE_PATCH"
git apply "$PATCH" >> "$RUN_LOG" 2>&1 || fail "code_patch_apply_failed" "REVIEW_PRIVATE_ARCHIVE_PATCH"
[ "$(git diff --name-only | wc -l | tr -d ' ')" = "2" ] || fail "reapplied_change_count_unexpected" "INSPECT_REAPPLIED_PATCH"
PATCH_REAPPLY="PASS"

git diff --check -- "$SOURCE" "$TEST_FILE" >> "$RUN_LOG" 2>&1 || fail "patch_whitespace_failed" "FIX_INTENT_BOUNDARY_PATCH"
PYTHONPATH="$ORIS:$ORIS/scripts" PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 - "$SOURCE" <<'PY' >> "$RUN_LOG" 2>&1
from pathlib import Path
import sys
compile(Path(sys.argv[1]).read_text(encoding='utf-8'),sys.argv[1],'exec')
PY
[ "$?" = "0" ] || fail "python_syntax_failed" "FIX_INTENT_BOUNDARY_CODE"
STATIC_CHECKS="PASS"

PYTHONPATH="$ORIS:$ORIS/scripts" PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest -v tests.test_dev_employee_openclaw_provider tests.test_dev_employee_agent_harness tests.test_dev_employee_chat_orchestrator tests.test_dev_employee_web_console_v3 >> "$RUN_LOG" 2>&1 || fail "intent_boundary_unittest_failed" "FIX_INTENT_BOUNDARY_TESTS"
TEST_RESULT="PASS"

PYTHONPATH="$ORIS:$ORIS/scripts" PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 - <<'PY' >> "$RUN_LOG" 2>&1
from scripts.dev_employee_openclaw_provider import DeterministicFallbackProvider, explicit_control_intent
m=("给 oris-final-acceptance-api 增加一个只读 GET /capabilities 接口，返回 service、storage 和 features 三个字段；features 至少包含 task_crud、filtering 和 stats。补充 pytest 覆盖接口状态码和字段契约，更新 README 的 API 列表，运行 py_compile 和 pytest，完成后提交并推送。不要修改 ORIS 平台代码或任何密钥。")
p=DeterministicFallbackProvider(); projects={"oris-final-acceptance-api":{"name":"ORIS Final Acceptance API","forbidden_scope":[".env","secrets"]}}; s={"selected_project":None,"current_task_id":None,"messages":[]}
assert not explicit_control_intent(m); assert p.is_risky(m) is None
r=p.analyze(session=s,user_message=m,projects=projects,current_task=None)
assert r.intent=="create_task" and r.project_key=="oris-final-acceptance-api"
for c,e in [("查看进度","status"),("请查看进度一下","status"),("停止任务","cancel"),("重试","retry"),("帮助","help")]: assert p.control_intent(c)==e
PY
[ "$?" = "0" ] || fail "exact_message_regression_failed" "FIX_INTENT_CLASSIFIER"
REGRESSION_MESSAGE="PASS"; CONTROL_COMMANDS="PASS"; NEGATED_SECRET_POLICY="PASS"

git add -- "$SOURCE" "$TEST_FILE" >> "$RUN_LOG" 2>&1 || fail "code_add_failed" "INSPECT_ORIS_GIT_STATE"
git commit -m "fix(dev-employee): harden conversational intent boundaries" >> "$RUN_LOG" 2>&1 || fail "code_commit_failed" "INSPECT_ORIS_GIT_STATE"
CODE_COMMIT="$(git rev-parse HEAD)"
git push origin main >> "$RUN_LOG" 2>&1 || fail "code_push_failed" "RESOLVE_GITHUB_PUSH"
CODE_PUSH="PASS"

systemctl --user restart oris-dev-employee-web-console.service >> "$RUN_LOG" 2>&1 || fail "web_restart_failed" "INSPECT_WEB_CONSOLE_SERVICE"
sleep 3
[ "$(service_state oris-dev-employee-web-console.service)" = "active" ] || fail "web_not_active" "INSPECT_WEB_CONSOLE_SERVICE"
SERVICE_RESTART="PASS"
HEALTH="$(curl -fsS http://127.0.0.1:18893/health 2>/dev/null || true)"
python3 - "$HEALTH" <<'PY' >> "$RUN_LOG" 2>&1
import json,sys
p=json.loads(sys.argv[1]);assert p.get('service')=='dev_employee_web_console_v5';assert p.get('agent_harness_enabled') is True;assert p.get('openclaw_provider_configured') is True
PY
[ "$?" = "0" ] || fail "web_health_failed" "INSPECT_WEB_CONSOLE_SERVICE"
WEB_HEALTH="PASS"

FINAL_PRODUCT_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
FINAL_PRODUCT_REMOTE="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n1)"
[ "$FINAL_PRODUCT_SHA" = "$BASE_PRODUCT_SHA" ] && [ "$FINAL_PRODUCT_REMOTE" = "$BASE_PRODUCT_SHA" ] || fail "product_sha_changed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_SHA_UNCHANGED="PASS"
[ -z "$(git -C "$PRODUCT" status --porcelain --untracked-files=no)" ] || fail "product_worktree_changed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_WORKTREE_CLEAN="PASS"
[ -z "$(git status --porcelain --untracked-files=no)" ] || fail "worktree_dirty_before_evidence" "INSPECT_ORIS_GIT_STATE"
FINAL_WORKTREE_CLEAN="PASS"

RESULT="PASS"; NEXT_ACTION="RETRY_CONTROLLED_BROWSER_TASK_ONCE"
write_evidence
commit_evidence || { RESULT="FAILED"; FAILURE_CODE="evidence_push_failed"; NEXT_ACTION="RESOLVE_EVIDENCE_PUSH"; }
if [ "$RESULT" = "PASS" ]; then
  git fetch origin main >/dev/null 2>&1
  git reset --mixed origin/main >/dev/null 2>&1
  git restore --source=origin/main --worktree -- . >/dev/null 2>&1
  [ -z "$(git status --porcelain --untracked-files=no)" ] || { RESULT="FAILED"; FAILURE_CODE="final_worktree_not_clean"; NEXT_ACTION="INSPECT_FINAL_GIT_STATE"; FINAL_WORKTREE_CLEAN="NO"; }
fi
summary
git worktree remove --force "$EVIDENCE_WT" >/dev/null 2>&1 || true
[ "$RESULT" = "PASS" ] && exit 0
exit 1
