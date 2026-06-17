#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
DOMAIN="control.orisfy.com"
OPENCLAW_URL="https://control.orisfy.com/"
ADMIN_URL="https://control.orisfy.com/admin"
ROLLBACK_URL="https://control.orisfy.com/_oris-chat-shell"
OPENCLAW_DIRECT="http://127.0.0.1:18789/"
INTAKE_PORT="18892"
EXPECTED_PRODUCT_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"
EXPECTED_PRODUCT_STATUS=" M README.md"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-native-openclaw-browser-acceptance-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/acceptance.log"
RESULT_JSON="$TMP_ROOT/acceptance.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/native_openclaw_ui_acceptance"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-acceptance-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-acceptance-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
AUTOMATED_PREFLIGHT="NOT_RUN"
MANUAL_ACCEPTANCE="NOT_RUN"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ADMIN_STATUS="000"
PUBLIC_ROLLBACK_STATUS="000"
PUBLIC_ROOT_MATCHES_DIRECT="NO"
INTAKE_LOOPBACK_ONLY="unknown"
PRODUCT_BASELINE_PRESERVED="NO"
FAILED_CHECKS=""
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_BROWSER_ACCEPTANCE_FAILURE"

umask 077
: > "$RUN_LOG"

cleanup() {
  if [ -d "$WORKTREE" ]; then
    git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

log() {
  printf '%s\n' "$*" >> "$RUN_LOG"
}

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "AUTOMATED_PREFLIGHT=$AUTOMATED_PREFLIGHT"
  echo "MANUAL_ACCEPTANCE=$MANUAL_ACCEPTANCE"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ADMIN_STATUS=$PUBLIC_ADMIN_STATUS"
  echo "PUBLIC_ROLLBACK_STATUS=$PUBLIC_ROLLBACK_STATUS"
  echo "PUBLIC_ROOT_MATCHES_DIRECT=$PUBLIC_ROOT_MATCHES_DIRECT"
  echo "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "FAILED_CHECKS=$FAILED_CHECKS"
  echo "CURRENT_TASK_UPDATED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "PRODUCT_REPOSITORY_MUTATED=NO"
  echo "EVIDENCE_LOG=$EVIDENCE_LOG_REL"
  echo "EVIDENCE_JSON=$EVIDENCE_JSON_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail_now() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  summary
  exit 1
}

ask_yes_no() {
  local key="$1"
  local prompt="$2"
  local answer=""
  while true; do
    printf '\n[%s]\n%s\n输入 y 表示通过，n 表示失败：' "$key" "$prompt"
    IFS= read -r answer
    case "$answer" in
      y|Y|yes|YES|Yes)
        printf '%s=PASS\n' "$key" >> "$RUN_LOG"
        printf 'PASS'
        return 0
        ;;
      n|N|no|NO|No)
        printf '%s=FAIL\n' "$key" >> "$RUN_LOG"
        printf 'FAIL'
        return 0
        ;;
      *)
        echo "只输入 y 或 n。"
        ;;
    esac
  done
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  fail_now "wrong_linux_user" "RUN_AS_ADMIN"
fi

for cmd in git curl python3 sha256sum ss; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done

[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=MANUAL_BROWSER_ACCEPTANCE_WITH_AUTOMATED_PREFLIGHT"
log "CURRENT_TASK_UPDATED=NO"
log "PRODUCT_TASK_SUBMITTED=NO"
log "PRODUCT_REPOSITORY_MUTATED=NO"

PUBLIC_ROOT_BODY="$TMP_ROOT/public-root.body"
DIRECT_ROOT_BODY="$TMP_ROOT/direct-root.body"
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 10 -o "$PUBLIC_ROOT_BODY" -w '%{http_code}' "$OPENCLAW_URL" 2>/dev/null || true)"
PUBLIC_ADMIN_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "$ADMIN_URL" 2>/dev/null || true)"
PUBLIC_ROLLBACK_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "$ROLLBACK_URL" 2>/dev/null || true)"
DIRECT_ROOT_STATUS="$(curl -sS --max-time 10 -o "$DIRECT_ROOT_BODY" -w '%{http_code}' "$OPENCLAW_DIRECT" 2>/dev/null || true)"
PUBLIC_SHA="$(sha256sum "$PUBLIC_ROOT_BODY" 2>/dev/null | awk '{print $1}')"
DIRECT_SHA="$(sha256sum "$DIRECT_ROOT_BODY" 2>/dev/null | awk '{print $1}')"

if [ -n "$PUBLIC_SHA" ] && [ "$PUBLIC_SHA" = "$DIRECT_SHA" ]; then
  PUBLIC_ROOT_MATCHES_DIRECT="YES"
fi

INTAKE_LISTENER="$(ss -ltn 2>/dev/null | awk -v p=":$INTAKE_PORT" '$4 ~ p"$" {print $4; exit}')"
case "$INTAKE_LISTENER" in
  127.0.0.1:*|\[::1\]:*) INTAKE_LOOPBACK_ONLY="YES" ;;
  *) INTAKE_LOOPBACK_ONLY="NO" ;;
esac

PRODUCT_HEAD="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_MAIN="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"

if [ "$PRODUCT_HEAD" = "$EXPECTED_PRODUCT_HEAD" ] && [ "$PRODUCT_REMOTE_MAIN" = "$EXPECTED_PRODUCT_HEAD" ] && [ "$PRODUCT_STATUS" = "$EXPECTED_PRODUCT_STATUS" ]; then
  PRODUCT_BASELINE_PRESERVED="YES"
fi

log "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
log "PUBLIC_ADMIN_STATUS=$PUBLIC_ADMIN_STATUS"
log "PUBLIC_ROLLBACK_STATUS=$PUBLIC_ROLLBACK_STATUS"
log "DIRECT_ROOT_STATUS=$DIRECT_ROOT_STATUS"
log "PUBLIC_ROOT_MATCHES_DIRECT=$PUBLIC_ROOT_MATCHES_DIRECT"
log "INTAKE_LISTENER=$INTAKE_LISTENER"
log "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
log "PRODUCT_HEAD=$PRODUCT_HEAD"
log "PRODUCT_REMOTE_MAIN=$PRODUCT_REMOTE_MAIN"
log "PRODUCT_STATUS=$PRODUCT_STATUS"
log "README_SHA256=$README_HASH"

if [ "$PUBLIC_ROOT_STATUS" = "200" ] && [ "$DIRECT_ROOT_STATUS" = "200" ] && [ "$PUBLIC_ROOT_MATCHES_DIRECT" = "YES" ] && { [ "$PUBLIC_ADMIN_STATUS" = "401" ] || [ "$PUBLIC_ADMIN_STATUS" = "403" ]; } && { [ "$PUBLIC_ROLLBACK_STATUS" = "401" ] || [ "$PUBLIC_ROLLBACK_STATUS" = "403" ]; } && [ "$INTAKE_LOOPBACK_ONLY" = "YES" ] && [ "$PRODUCT_BASELINE_PRESERVED" = "YES" ]; then
  AUTOMATED_PREFLIGHT="PASS"
else
  AUTOMATED_PREFLIGHT="FAIL"
  fail_now "automated_browser_acceptance_preflight_failed" "RUN_NGINX_ROLLBACK_OR_INSPECT_MIGRATION_EVIDENCE"
fi

echo
echo "浏览器验收开始。"
echo "只在你自己的浏览器中输入现有认证信息；不要在终端、聊天或本脚本中输入 Token、密码或配对码。"
echo "主入口：$OPENCLAW_URL"
echo "管理入口：$ADMIN_URL"
echo "受限回滚入口：$ROLLBACK_URL"
echo

CHECK_KEYS=(
  ROOT_IS_NATIVE_OPENCLAW
  AUTH_OR_DEVICE_PAIRING_WORKS
  NEW_CONVERSATION_WORKS
  FIRST_MESSAGE_RESPONSE_WORKS
  SECOND_CONVERSATION_WORKS
  HISTORY_LIST_VISIBLE
  SWITCH_PRESERVES_FIRST_CONVERSATION
  CLEAR_OR_ARCHIVE_SECOND_CONVERSATION
  REFRESH_PRESERVES_HISTORY
  ADMIN_REQUIRES_AUTH_AND_LOADS
  ROLLBACK_ROUTE_REQUIRES_AUTH_AND_LOADS
  NO_CRITICAL_BLANK_OR_DISCONNECT
)

CHECK_PROMPTS=(
  "打开主入口，确认显示 OpenClaw 原生界面，而不是 ORIS Web Console v5。"
  "如界面要求认证或设备配对，使用现有方式完成；确认无需暴露任何 Token，并能进入主界面。"
  "新建第一个对话，确认创建成功。"
  "在第一个对话发送：Reply exactly: ORIS_NATIVE_UI_ACCEPTED_1；确认收到正常回复。"
  "再新建第二个对话，确认两个对话是独立会话。"
  "确认历史/会话列表中能够看到第一个和第二个对话。"
  "切回第一个对话，确认之前的消息与回复仍完整存在。"
  "对第二个对话执行界面实际提供的清空、归档或删除动作；确认第一个对话不受影响。"
  "刷新页面或关闭后重新打开主入口，确认第一个对话历史仍可访问。"
  "打开 /admin：确认先出现认证限制；使用现有管理认证后，ORIS Web Console 能加载。"
  "打开 /_oris-chat-shell：确认先出现认证限制；使用现有管理认证后，诊断/回滚 Console 能加载。"
  "整个过程没有持续空白页、静态资源加载失败、持续断线或无法恢复的会话错误。"
)

PASS_COUNT=0
FAIL_COUNT=0
MANUAL_RESULTS_JSON="$TMP_ROOT/manual-results.jsonl"
: > "$MANUAL_RESULTS_JSON"

for index in "${!CHECK_KEYS[@]}"; do
  key="${CHECK_KEYS[$index]}"
  prompt="${CHECK_PROMPTS[$index]}"
  outcome="$(ask_yes_no "$key" "$prompt")"
  printf '{"check":"%s","result":"%s"}\n' "$key" "$outcome" >> "$MANUAL_RESULTS_JSON"
  if [ "$outcome" = "PASS" ]; then
    PASS_COUNT=$((PASS_COUNT+1))
  else
    FAIL_COUNT=$((FAIL_COUNT+1))
    if [ -z "$FAILED_CHECKS" ]; then
      FAILED_CHECKS="$key"
    else
      FAILED_CHECKS="$FAILED_CHECKS,$key"
    fi
  fi
done

if [ "$FAIL_COUNT" -eq 0 ]; then
  MANUAL_ACCEPTANCE="PASS"
  RESULT="ACCEPTED"
  NEXT_ACTION="REPAIR_EXISTING_PRODUCT_README_GAP_RUN_TESTS_COMMIT_PUSH_AND_VERIFY_EVIDENCE"
else
  MANUAL_ACCEPTANCE="FAIL"
  RESULT="REJECTED"
  FAILURE_CODE="manual_browser_acceptance_failed"
  NEXT_ACTION="RUN_NATIVE_OPENCLAW_NGINX_ROLLBACK_AND_INSPECT_FAILED_CHECKS"
fi

export TASK_ID STAMP RESULT FAILURE_CODE AUTOMATED_PREFLIGHT MANUAL_ACCEPTANCE PUBLIC_ROOT_STATUS PUBLIC_ADMIN_STATUS PUBLIC_ROLLBACK_STATUS PUBLIC_ROOT_MATCHES_DIRECT INTAKE_LOOPBACK_ONLY PRODUCT_BASELINE_PRESERVED PRODUCT_HEAD PRODUCT_REMOTE_MAIN PRODUCT_STATUS README_HASH PASS_COUNT FAIL_COUNT FAILED_CHECKS NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$MANUAL_RESULTS_JSON" "$RESULT_JSON" <<'PY'
import json
import os
import sys
from pathlib import Path

manual=[]
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.strip():
        manual.append(json.loads(line))

payload={
    "task_id":os.environ.get("TASK_ID"),
    "checked_at":os.environ.get("STAMP"),
    "result":os.environ.get("RESULT"),
    "failure_code":os.environ.get("FAILURE_CODE"),
    "automated_preflight":os.environ.get("AUTOMATED_PREFLIGHT"),
    "manual_acceptance":os.environ.get("MANUAL_ACCEPTANCE"),
    "public":{
        "root_status":os.environ.get("PUBLIC_ROOT_STATUS"),
        "admin_without_credentials_status":os.environ.get("PUBLIC_ADMIN_STATUS"),
        "rollback_without_credentials_status":os.environ.get("PUBLIC_ROLLBACK_STATUS"),
        "root_matches_direct_openclaw":os.environ.get("PUBLIC_ROOT_MATCHES_DIRECT")=="YES",
    },
    "safety":{
        "intake_loopback_only":os.environ.get("INTAKE_LOOPBACK_ONLY")=="YES",
        "product_baseline_preserved":os.environ.get("PRODUCT_BASELINE_PRESERVED")=="YES",
        "current_task_updated":False,
        "product_task_submitted":False,
        "product_repository_mutated":False,
        "secret_values_recorded":False,
    },
    "product":{
        "head":os.environ.get("PRODUCT_HEAD"),
        "remote_main":os.environ.get("PRODUCT_REMOTE_MAIN"),
        "status":os.environ.get("PRODUCT_STATUS"),
        "readme_sha256":os.environ.get("README_HASH"),
    },
    "manual_checks":manual,
    "pass_count":int(os.environ.get("PASS_COUNT","0")),
    "fail_count":int(os.environ.get("FAIL_COUNT","0")),
    "failed_checks":[x for x in os.environ.get("FAILED_CHECKS","").split(",") if x],
    "evidence":{
        "log_path":os.environ.get("EVIDENCE_LOG_REL"),
        "json_path":os.environ.get("EVIDENCE_JSON_REL"),
        "self_commit_sha_omitted_to_prevent_post_commit_log_drift":True,
    },
    "next_action":os.environ.get("NEXT_ACTION"),
}
Path(sys.argv[2]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY'
import re
import sys
from pathlib import Path
patterns=[
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
]
for filename in sys.argv[1:]:
    text=Path(filename).read_text(encoding="utf-8",errors="replace")
    if any(p.search(text) for p in patterns):
        raise SystemExit(1)
PY
if [ "$?" -ne 0 ]; then
  fail_now "acceptance_evidence_secret_scan_failed" "REPAIR_ACCEPTANCE_EVIDENCE_REDACTION"
fi

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY'
import json
import sys
from pathlib import Path
src_log,dst_log,src_json,dst_json=map(Path,sys.argv[1:])
lines=[line.rstrip(" \t\r") for line in src_log.read_text(encoding="utf-8",errors="replace").splitlines()]
dst_log.write_text("\n".join(lines)+"\n",encoding="utf-8")
payload=json.loads(src_json.read_text(encoding="utf-8"))
dst_json.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY
[ "$?" -eq 0 ] || fail_now "evidence_normalization_failed" "INSPECT_ACCEPTANCE_EVIDENCE"
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native OpenClaw browser acceptance $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then
  EVIDENCE_REMOTE_VERIFIED="YES"
else
  RESULT="FAILED"
  FAILURE_CODE="evidence_remote_sha_mismatch"
  NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"
fi

summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
