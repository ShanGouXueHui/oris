#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
DOMAIN="control.orisfy.com"
OPENCLAW_URL="https://control.orisfy.com/"
ADMIN_URL="https://control.orisfy.com/admin"
ROLLBACK_URL="https://control.orisfy.com/_oris-chat-shell"
OPENCLAW_DIRECT="http://127.0.0.1:18789/"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
TOKEN_FILE="$HOME/.openclaw/private/control-orisfy-gateway-token-current.txt"
DASHBOARD_URL_FILE="$HOME/.openclaw/private/control-orisfy-dashboard-url-current.txt"
INTAKE_PORT="18892"
EXPECTED_PRODUCT_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"
EXPECTED_PRODUCT_STATUS=" M README.md"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-native-openclaw-browser-v2-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/acceptance.log"
RESULT_JSON="$TMP_ROOT/acceptance.json"
MANUAL_RESULTS="$TMP_ROOT/manual-results.jsonl"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/native_openclaw_ui_acceptance"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-acceptance-v2-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-acceptance-v2-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
AUTOMATED_PREFLIGHT="NOT_RUN"
MANUAL_ACCEPTANCE="NOT_RUN"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ADMIN_STATUS="000"
PUBLIC_ROLLBACK_STATUS="000"
PUBLIC_BOOTSTRAP_STATUS="000"
PUBLIC_SESSION_STATUS="000"
PUBLIC_MESSAGES_STATUS="000"
PUBLIC_ROOT_MATCHES_DIRECT="NO"
NGINX_CONFLICT_WARNING_COUNT="unknown"
PRIVATE_TOKEN_VALID="NO"
INTAKE_LOOPBACK_ONLY="unknown"
PRODUCT_BASELINE_PRESERVED="NO"
FAILED_CHECKS=""
PASS_COUNT=0
FAIL_COUNT=0
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_BROWSER_ACCEPTANCE_V2_FAILURE"
ANSWER_RESULT=""

umask 077
: > "$RUN_LOG"
: > "$MANUAL_RESULTS"

cleanup() {
  if [ -d "$WORKTREE" ]; then
    git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

log() { printf '%s\n' "$*" >> "$RUN_LOG"; }

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
  echo "PUBLIC_BOOTSTRAP_STATUS=$PUBLIC_BOOTSTRAP_STATUS"
  echo "PUBLIC_SESSION_STATUS=$PUBLIC_SESSION_STATUS"
  echo "PUBLIC_MESSAGES_STATUS=$PUBLIC_MESSAGES_STATUS"
  echo "PUBLIC_ROOT_MATCHES_DIRECT=$PUBLIC_ROOT_MATCHES_DIRECT"
  echo "NGINX_CONFLICT_WARNING_COUNT=$NGINX_CONFLICT_WARNING_COUNT"
  echo "PRIVATE_TOKEN_VALID=$PRIVATE_TOKEN_VALID"
  echo "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "PASS_COUNT=$PASS_COUNT"
  echo "FAIL_COUNT=$FAIL_COUNT"
  echo "FAILED_CHECKS=$FAILED_CHECKS"
  echo "CURRENT_TASK_UPDATED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "PRODUCT_REPOSITORY_MUTATED=NO"
  echo "OPENCLAW_CONFIG_MUTATED=NO"
  echo "TOKEN_RECORDED_IN_EVIDENCE=NO"
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
  ANSWER_RESULT=""
  while true; do
    printf '\n[%s]\n%s\n输入 y 表示通过，n 表示失败：' "$key" "$prompt" > /dev/tty
    IFS= read -r answer < /dev/tty
    case "$answer" in
      y|Y|yes|YES|Yes)
        ANSWER_RESULT="PASS"
        log "$key=PASS"
        return 0
        ;;
      n|N|no|NO|No)
        ANSWER_RESULT="FAIL"
        log "$key=FAIL"
        return 0
        ;;
      *)
        printf '只输入 y 或 n。\n' > /dev/tty
        ;;
    esac
  done
}

record_result() {
  local key="$1"
  local outcome="$2"
  printf '{"check":"%s","result":"%s"}\n' "$key" "$outcome" >> "$MANUAL_RESULTS"
  if [ "$outcome" = "PASS" ]; then
    PASS_COUNT=$((PASS_COUNT+1))
  else
    FAIL_COUNT=$((FAIL_COUNT+1))
    if [ -z "$FAILED_CHECKS" ]; then FAILED_CHECKS="$key"; else FAILED_CHECKS="$FAILED_CHECKS,$key"; fi
  fi
}

show_token_once() {
  local answer=""
  printf '\n需要把服务器本地的新 Gateway Token 粘贴到浏览器。\n' > /dev/tty
  printf 'Token 只会临时显示在本终端，不会写入日志或 GitHub。\n' > /dev/tty
  printf '确认周围无人、未开启录屏且不会截图后，输入 SHOW：' > /dev/tty
  IFS= read -r answer < /dev/tty
  if [ "$answer" != "SHOW" ]; then
    return 1
  fi
  printf '\n===== PRIVATE GATEWAY TOKEN — DO NOT SCREENSHOT =====\n' > /dev/tty
  cat "$TOKEN_FILE" > /dev/tty
  printf '===== END PRIVATE TOKEN =====\n' > /dev/tty
  printf '复制完成后按 Enter，终端将立即清屏：' > /dev/tty
  IFS= read -r answer < /dev/tty
  clear > /dev/tty 2>/dev/null || printf '\033[2J\033[H' > /dev/tty
  return 0
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user" "RUN_AS_ADMIN"; fi
for cmd in git curl python3 sha256sum ss stat sudo nginx grep cat clear; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -t 0 ] || fail_now "interactive_tty_required" "RUN_IN_INTERACTIVE_SSH_TERMINAL"
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$OPENCLAW_CONFIG" ] || fail_now "openclaw_config_missing" "RESTORE_OPENCLAW_CONFIG"
[ -f "$TOKEN_FILE" ] || fail_now "private_token_file_missing" "FINALIZE_OPENCLAW_TOKEN_ROTATION"
[ -f "$DASHBOARD_URL_FILE" ] || fail_now "private_dashboard_url_missing" "FINALIZE_OPENCLAW_TOKEN_ROTATION"
[ "$(stat -c '%a' "$TOKEN_FILE" 2>/dev/null)" = "600" ] || fail_now "private_token_file_not_0600" "RESTORE_PRIVATE_FILE_PERMISSIONS"
[ "$(stat -c '%a' "$DASHBOARD_URL_FILE" 2>/dev/null)" = "600" ] || fail_now "private_dashboard_url_not_0600" "RESTORE_PRIVATE_FILE_PERMISSIONS"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=NATIVE_OPENCLAW_BROWSER_ACCEPTANCE_V2"
log "TOKEN_RECORDED_IN_EVIDENCE=NO"
log "CURRENT_TASK_UPDATED=NO"
log "PRODUCT_TASK_SUBMITTED=NO"
log "PRODUCT_REPOSITORY_MUTATED=NO"

PUBLIC_ROOT_BODY="$TMP_ROOT/public-root.body"
DIRECT_ROOT_BODY="$TMP_ROOT/direct-root.body"
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 10 -H 'Cache-Control: no-cache' -o "$PUBLIC_ROOT_BODY" -w '%{http_code}' "$OPENCLAW_URL" 2>/dev/null || true)"
DIRECT_ROOT_STATUS="$(curl -sS --max-time 10 -H 'Cache-Control: no-cache' -o "$DIRECT_ROOT_BODY" -w '%{http_code}' "$OPENCLAW_DIRECT" 2>/dev/null || true)"
PUBLIC_ADMIN_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "$ADMIN_URL" 2>/dev/null || true)"
PUBLIC_ROLLBACK_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "$ROLLBACK_URL" 2>/dev/null || true)"
PUBLIC_BOOTSTRAP_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/api/chat/bootstrap" 2>/dev/null || true)"
PUBLIC_SESSION_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/api/chat/session" 2>/dev/null || true)"
PUBLIC_MESSAGES_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/api/chat/messages" 2>/dev/null || true)"
PUBLIC_SHA="$(sha256sum "$PUBLIC_ROOT_BODY" 2>/dev/null | awk '{print $1}')"
DIRECT_SHA="$(sha256sum "$DIRECT_ROOT_BODY" 2>/dev/null | awk '{print $1}')"
if [ -n "$PUBLIC_SHA" ] && [ "$PUBLIC_SHA" = "$DIRECT_SHA" ]; then PUBLIC_ROOT_MATCHES_DIRECT="YES"; fi

NGINX_DUMP="$TMP_ROOT/nginx-T.txt"
sudo -n nginx -T > "$NGINX_DUMP" 2>&1 || fail_now "nginx_dump_failed" "INSPECT_EFFECTIVE_NGINX_CONFIG"
NGINX_CONFLICT_WARNING_COUNT="$(grep -Eic 'conflicting server name.*control\.orisfy\.com' "$NGINX_DUMP" || true)"

INTAKE_LISTENER="$(ss -ltn 2>/dev/null | awk -v p=":$INTAKE_PORT" '$4 ~ p"$" {print $4; exit}')"
case "$INTAKE_LISTENER" in 127.0.0.1:*|\[::1\]:*) INTAKE_LOOPBACK_ONLY="YES" ;; *) INTAKE_LOOPBACK_ONLY="NO" ;; esac

PRODUCT_HEAD="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_MAIN="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
if [ "$PRODUCT_HEAD" = "$EXPECTED_PRODUCT_HEAD" ] && [ "$PRODUCT_REMOTE_MAIN" = "$EXPECTED_PRODUCT_HEAD" ] && [ "$PRODUCT_STATUS" = "$EXPECTED_PRODUCT_STATUS" ]; then PRODUCT_BASELINE_PRESERVED="YES"; fi

python3 - "$OPENCLAW_CONFIG" "$TOKEN_FILE" "$DASHBOARD_URL_FILE" "$DOMAIN" "$TMP_ROOT/private-safe.json" <<'PY_PRIVATE'
import json,sys
from pathlib import Path
from urllib.parse import unquote,urlsplit
config=Path(sys.argv[1]); token_file=Path(sys.argv[2]); url_file=Path(sys.argv[3]); domain=sys.argv[4]; out=Path(sys.argv[5])
data=json.loads(config.read_text(encoding="utf-8"))
config_token=data.get("gateway",{}).get("auth",{}).get("token")
private_token=token_file.read_text(encoding="utf-8").strip()
private_url=url_file.read_text(encoding="utf-8").strip()
parsed=urlsplit(private_url)
valid=(data.get("gateway",{}).get("auth",{}).get("mode")=="token" and isinstance(config_token,str) and config_token and private_token==config_token and parsed.scheme=="https" and parsed.hostname==domain and private_token not in unquote(private_url))
out.write_text(json.dumps({"valid":bool(valid),"dashboard_url":private_url if valid else None,"secret_values_recorded":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_PRIVATE
[ "$?" -eq 0 ] || fail_now "private_token_validation_failed" "FINALIZE_OPENCLAW_TOKEN_ROTATION"
PRIVATE_TOKEN_VALID="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["valid"] else "NO")' "$TMP_ROOT/private-safe.json")"
DASHBOARD_URL="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["dashboard_url"] or "")' "$TMP_ROOT/private-safe.json")"

log "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
log "DIRECT_ROOT_STATUS=$DIRECT_ROOT_STATUS"
log "PUBLIC_ROOT_MATCHES_DIRECT=$PUBLIC_ROOT_MATCHES_DIRECT"
log "PUBLIC_ADMIN_STATUS=$PUBLIC_ADMIN_STATUS"
log "PUBLIC_ROLLBACK_STATUS=$PUBLIC_ROLLBACK_STATUS"
log "PUBLIC_BOOTSTRAP_STATUS=$PUBLIC_BOOTSTRAP_STATUS"
log "PUBLIC_SESSION_STATUS=$PUBLIC_SESSION_STATUS"
log "PUBLIC_MESSAGES_STATUS=$PUBLIC_MESSAGES_STATUS"
log "NGINX_CONFLICT_WARNING_COUNT=$NGINX_CONFLICT_WARNING_COUNT"
log "PRIVATE_TOKEN_VALID=$PRIVATE_TOKEN_VALID"
log "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
log "PRODUCT_HEAD=$PRODUCT_HEAD"
log "PRODUCT_REMOTE_MAIN=$PRODUCT_REMOTE_MAIN"
log "PRODUCT_STATUS=$PRODUCT_STATUS"
log "README_SHA256=$README_HASH"

ALL_RESTRICTED="YES"
for status in "$PUBLIC_ADMIN_STATUS" "$PUBLIC_ROLLBACK_STATUS" "$PUBLIC_BOOTSTRAP_STATUS" "$PUBLIC_SESSION_STATUS" "$PUBLIC_MESSAGES_STATUS"; do
  case "$status" in 401|403) ;; *) ALL_RESTRICTED="NO" ;; esac
done
if [ "$PUBLIC_ROOT_STATUS" = "200" ] && [ "$DIRECT_ROOT_STATUS" = "200" ] && [ "$PUBLIC_ROOT_MATCHES_DIRECT" = "YES" ] && [ "$ALL_RESTRICTED" = "YES" ] && [ "$NGINX_CONFLICT_WARNING_COUNT" = "0" ] && [ "$PRIVATE_TOKEN_VALID" = "YES" ] && [ "$INTAKE_LOOPBACK_ONLY" = "YES" ] && [ "$PRODUCT_BASELINE_PRESERVED" = "YES" ]; then
  AUTOMATED_PREFLIGHT="PASS"
else
  AUTOMATED_PREFLIGHT="FAIL"
  fail_now "automated_browser_acceptance_v2_preflight_failed" "RUN_NATIVE_OPENCLAW_NGINX_ROLLBACK_V2_OR_INSPECT_MIGRATION_EVIDENCE"
fi

printf '\n浏览器验收 v2 开始。\n' > /dev/tty
printf '必须使用无痕/隐私窗口，避免复用第一次失败时缓存的旧 Token。\n' > /dev/tty
printf 'Dashboard URL（不含 Token）：%s\n' "$DASHBOARD_URL" > /dev/tty
printf '在浏览器中打开该 URL；Gateway Token 使用下一步临时显示的新 Token，Password 留空。\n' > /dev/tty

show_token_once || fail_now "private_token_not_displayed" "RERUN_ACCEPTANCE_V2_WHEN_READY"

CHECK_KEYS=(
  INCOGNITO_AND_NATIVE_UI
  TOKEN_AUTH_CONNECTED
  NEW_CONVERSATION_WORKS
  FIRST_MESSAGE_RESPONSE_WORKS
  SECOND_CONVERSATION_WORKS
  HISTORY_LIST_VISIBLE
  SWITCH_PRESERVES_FIRST_CONVERSATION
  CLEAR_OR_ARCHIVE_SECOND_CONVERSATION
  REFRESH_PRESERVES_HISTORY
  ADMIN_CONSOLE_LOADS_WITHOUT_HTTP404
  ROLLBACK_CONSOLE_LOADS_WITHOUT_HTTP404
  NO_CRITICAL_BLANK_OR_DISCONNECT
)
CHECK_PROMPTS=(
  "已在无痕/隐私窗口打开 Dashboard URL，页面是 OpenClaw 原生 UI，不是 ORIS Web Console v5。"
  "把新 Token 粘贴到 Gateway Token，Password 保持空白并点击连接；页面显示已连接，不再出现认证不匹配。"
  "新建第一个对话，确认创建成功。"
  "在第一个对话发送 Reply exactly: ORIS_NATIVE_UI_ACCEPTED_2，并收到正常回复。"
  "新建第二个独立对话，确认没有覆盖第一个对话。"
  "历史/会话列表能看到第一个和第二个对话。"
  "切回第一个对话，之前的消息和回复完整保留。"
  "对第二个对话执行界面提供的清空、归档或删除动作，第一个对话不受影响。"
  "刷新或关闭后重新打开同一无痕窗口中的 Dashboard URL，第一个对话历史仍可访问。"
  "打开 /admin，先出现 Basic Auth；认证后 ORIS Console 正常加载，页面不再显示 HTTP 404。"
  "打开 /_oris-chat-shell，先出现 Basic Auth；认证后诊断 Console 正常加载，页面不再显示 HTTP 404。"
  "全过程没有持续空白页、关键静态资源失败、持续断线或无法恢复的错误。"
)

for index in "${!CHECK_KEYS[@]}"; do
  key="${CHECK_KEYS[$index]}"
  prompt="${CHECK_PROMPTS[$index]}"
  ask_yes_no "$key" "$prompt"
  record_result "$key" "$ANSWER_RESULT"
done

if [ "$FAIL_COUNT" -eq 0 ]; then
  MANUAL_ACCEPTANCE="PASS"
  RESULT="ACCEPTED_V2"
  NEXT_ACTION="COMPLETE_EXISTING_PRODUCT_README_GAP_RUN_TESTS_COMMIT_PUSH_AND_VERIFY_EVIDENCE"
else
  MANUAL_ACCEPTANCE="FAIL"
  RESULT="REJECTED_V2"
  FAILURE_CODE="manual_browser_acceptance_v2_failed"
  NEXT_ACTION="RUN_NATIVE_OPENCLAW_NGINX_ROLLBACK_V2_AND_INSPECT_FAILED_CHECKS"
fi

export TASK_ID STAMP RESULT FAILURE_CODE AUTOMATED_PREFLIGHT MANUAL_ACCEPTANCE PUBLIC_ROOT_STATUS PUBLIC_ADMIN_STATUS PUBLIC_ROLLBACK_STATUS PUBLIC_BOOTSTRAP_STATUS PUBLIC_SESSION_STATUS PUBLIC_MESSAGES_STATUS PUBLIC_ROOT_MATCHES_DIRECT NGINX_CONFLICT_WARNING_COUNT PRIVATE_TOKEN_VALID INTAKE_LOOPBACK_ONLY PRODUCT_BASELINE_PRESERVED PRODUCT_HEAD PRODUCT_REMOTE_MAIN PRODUCT_STATUS README_HASH PASS_COUNT FAIL_COUNT FAILED_CHECKS NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$MANUAL_RESULTS" "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path
manual=[json.loads(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
payload={
 "task_id":os.environ.get("TASK_ID"),"checked_at":os.environ.get("STAMP"),"result":os.environ.get("RESULT"),"failure_code":os.environ.get("FAILURE_CODE"),"automated_preflight":os.environ.get("AUTOMATED_PREFLIGHT"),"manual_acceptance":os.environ.get("MANUAL_ACCEPTANCE"),
 "public":{"root_status":os.environ.get("PUBLIC_ROOT_STATUS"),"admin_without_credentials":os.environ.get("PUBLIC_ADMIN_STATUS"),"rollback_without_credentials":os.environ.get("PUBLIC_ROLLBACK_STATUS"),"bootstrap_without_credentials":os.environ.get("PUBLIC_BOOTSTRAP_STATUS"),"session_without_credentials":os.environ.get("PUBLIC_SESSION_STATUS"),"messages_without_credentials":os.environ.get("PUBLIC_MESSAGES_STATUS"),"root_matches_direct_openclaw":os.environ.get("PUBLIC_ROOT_MATCHES_DIRECT")=="YES"},
 "manual_checks":manual,"pass_count":int(os.environ.get("PASS_COUNT","0")),"fail_count":int(os.environ.get("FAIL_COUNT","0")),"failed_checks":[x for x in os.environ.get("FAILED_CHECKS","").split(",") if x],
 "safety":{"nginx_conflict_warning_count":int(os.environ.get("NGINX_CONFLICT_WARNING_COUNT","-1")),"private_token_valid":os.environ.get("PRIVATE_TOKEN_VALID")=="YES","intake_loopback_only":os.environ.get("INTAKE_LOOPBACK_ONLY")=="YES","product_baseline_preserved":os.environ.get("PRODUCT_BASELINE_PRESERVED")=="YES","current_task_updated":False,"product_task_submitted":False,"product_repository_mutated":False,"openclaw_config_mutated":False,"token_recorded_in_evidence":False},
 "product":{"head":os.environ.get("PRODUCT_HEAD"),"remote_main":os.environ.get("PRODUCT_REMOTE_MAIN"),"status":os.environ.get("PRODUCT_STATUS"),"readme_sha256":os.environ.get("README_HASH")},
 "next_action":os.environ.get("NEXT_ACTION"),"evidence":{"log_path":os.environ.get("EVIDENCE_LOG_REL"),"json_path":os.environ.get("EVIDENCE_JSON_REL"),"self_commit_sha_omitted_to_prevent_post_commit_log_drift":True}
}
Path(sys.argv[2]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_RESULT

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY_SECRET_SCAN'
import re,sys
from pathlib import Path
patterns=[re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),re.compile(r"(?i)(gateway[_ -]?token|password|authorization|credential)(\s*[=:]\s*|\s+)(?!<redacted>|true\b|false\b|yes\b|no\b|null\b)[A-Za-z0-9._~+/-]{20,}")]
for filename in sys.argv[1:]:
 text=Path(filename).read_text(encoding="utf-8",errors="replace")
 if any(pattern.search(text) for pattern in patterns): raise SystemExit(1)
PY_SECRET_SCAN
[ "$?" -eq 0 ] || fail_now "acceptance_v2_evidence_secret_scan_failed" "REPAIR_ACCEPTANCE_V2_REDACTION"

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_NORMALIZE'
import json,sys
from pathlib import Path
sl,dl,sj,dj=map(Path,sys.argv[1:])
dl.write_text("\n".join(line.rstrip(" \t\r") for line in sl.read_text(encoding="utf-8",errors="replace").splitlines())+"\n",encoding="utf-8")
dj.write_text(json.dumps(json.loads(sj.read_text(encoding="utf-8")),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_NORMALIZE
[ "$?" -eq 0 ] || fail_now "evidence_normalization_failed" "INSPECT_ACCEPTANCE_V2_EVIDENCE"
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native OpenClaw browser acceptance v2 $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"; fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then EVIDENCE_REMOTE_VERIFIED="YES"; else RESULT="FAILED"; FAILURE_CODE="evidence_remote_sha_mismatch"; NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"; fi

summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
