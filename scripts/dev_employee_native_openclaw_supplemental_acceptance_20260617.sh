#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
OPENCLAW_URL="https://control.orisfy.com/"
SESSIONS_URL="https://control.orisfy.com/sessions"
OPENCLAW_DIRECT="http://127.0.0.1:18789/"
PREVIOUS_EVIDENCE="logs/dev_employee/native_openclaw_ui_acceptance/native-openclaw-ui-acceptance-v2-20260617T212356Z.json"
EXPECTED_PRODUCT_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"
EXPECTED_PRODUCT_STATUS=" M README.md"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-native-openclaw-supplemental-${STAMP}-XXXXXX)"
BEFORE_RAW="$TMP_ROOT/sessions-before.json"
AFTER_RAW="$TMP_ROOT/sessions-after.json"
BEFORE_SAFE="$TMP_ROOT/sessions-before-safe.json"
AFTER_SAFE="$TMP_ROOT/sessions-after-safe.json"
COMPARE_JSON="$TMP_ROOT/compare.json"
RUN_LOG="$TMP_ROOT/supplemental.log"
RESULT_JSON="$TMP_ROOT/supplemental.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/native_openclaw_ui_acceptance"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-supplemental-acceptance-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-supplemental-acceptance-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
AUTOMATED_PREFLIGHT="NOT_RUN"
PREVIOUS_ACCEPTANCE_SUPERSEDED="YES"
SESSION_DELETE_VERIFIED="NO"
FIRST_SESSION_PRESERVED="NO"
DASHBOARD_SESSION_COUNT_BEFORE="unknown"
DASHBOARD_SESSION_COUNT_AFTER="unknown"
DELETED_SESSION_COUNT="unknown"
RETAINED_SESSION_COUNT="unknown"
LATENCY_SAMPLE_COUNT="0"
LATEST_RUNTIME_MS="unknown"
MEDIAN_RUNTIME_MS="unknown"
MAX_RUNTIME_MS="unknown"
LATENCY_CLASSIFICATION="UNKNOWN"
PRODUCT_BASELINE_PRESERVED="NO"
FINAL_ACCEPTANCE="PENDING"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_SUPPLEMENTAL_ACCEPTANCE_FAILURE"

umask 077
: > "$RUN_LOG"

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
  echo "PREVIOUS_ACCEPTANCE_SUPERSEDED=$PREVIOUS_ACCEPTANCE_SUPERSEDED"
  echo "SESSION_DELETE_VERIFIED=$SESSION_DELETE_VERIFIED"
  echo "FIRST_SESSION_PRESERVED=$FIRST_SESSION_PRESERVED"
  echo "DASHBOARD_SESSION_COUNT_BEFORE=$DASHBOARD_SESSION_COUNT_BEFORE"
  echo "DASHBOARD_SESSION_COUNT_AFTER=$DASHBOARD_SESSION_COUNT_AFTER"
  echo "DELETED_SESSION_COUNT=$DELETED_SESSION_COUNT"
  echo "RETAINED_SESSION_COUNT=$RETAINED_SESSION_COUNT"
  echo "LATENCY_SAMPLE_COUNT=$LATENCY_SAMPLE_COUNT"
  echo "LATEST_RUNTIME_MS=$LATEST_RUNTIME_MS"
  echo "MEDIAN_RUNTIME_MS=$MEDIAN_RUNTIME_MS"
  echo "MAX_RUNTIME_MS=$MAX_RUNTIME_MS"
  echo "LATENCY_CLASSIFICATION=$LATENCY_CLASSIFICATION"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "FINAL_ACCEPTANCE=$FINAL_ACCEPTANCE"
  echo "CURRENT_TASK_UPDATED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "PRODUCT_REPOSITORY_MUTATED=NO"
  echo "OPENCLAW_CONFIG_MUTATED=NO"
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

capture_sessions() {
  local output="$1"
  if openclaw sessions --all-agents --limit all --json > "$output" 2>> "$RUN_LOG"; then
    return 0
  fi
  if openclaw sessions --all-agents --json > "$output" 2>> "$RUN_LOG"; then
    return 0
  fi
  if openclaw sessions --json > "$output" 2>> "$RUN_LOG"; then
    return 0
  fi
  return 1
}

sanitize_sessions() {
  local source="$1"
  local target="$2"
  python3 - "$source" "$target" <<'PY_SAFE'
import hashlib
import json
import statistics
import sys
from pathlib import Path

source=Path(sys.argv[1])
target=Path(sys.argv[2])
data=json.loads(source.read_text(encoding="utf-8"))

rows=[]
def walk(value):
    if isinstance(value,dict):
        sessions=value.get("sessions")
        if isinstance(sessions,list):
            for row in sessions:
                if isinstance(row,dict):
                    rows.append(row)
        for child in value.values():
            walk(child)
    elif isinstance(value,list):
        for child in value:
            walk(child)
walk(data)

unique={}
for row in rows:
    key=row.get("key")
    if not isinstance(key,str) or not key:
        continue
    unique[key]=row

def is_dashboard(key,row):
    surface=str(row.get("surface") or "").lower()
    return surface=="dashboard" or ":dashboard:" in key or key.endswith(":dashboard")

safe=[]
for key,row in unique.items():
    if not is_dashboard(key,row):
        continue
    runtime=row.get("runtimeMs")
    if not isinstance(runtime,(int,float)) or runtime < 0:
        runtime=None
    safe.append({
        "key_hash":hashlib.sha256(key.encode()).hexdigest(),
        "updated_at":row.get("updatedAt"),
        "started_at":row.get("startedAt"),
        "ended_at":row.get("endedAt"),
        "runtime_ms":runtime,
        "status":row.get("status"),
        "archived":row.get("archived") is True,
        "model":row.get("model"),
        "model_provider":row.get("modelProvider"),
    })
safe.sort(key=lambda x: x.get("updated_at") or 0,reverse=True)
runtimes=[float(x["runtime_ms"]) for x in safe[:10] if x.get("runtime_ms") is not None]
payload={
    "dashboard_session_count":len(safe),
    "sessions":safe[:30],
    "latency":{
        "sample_count":len(runtimes),
        "latest_runtime_ms":runtimes[0] if runtimes else None,
        "median_runtime_ms":statistics.median(runtimes) if runtimes else None,
        "max_runtime_ms":max(runtimes) if runtimes else None,
        "scope":"Latest runtimeMs values exposed by OpenClaw session metadata; not browser rendering time.",
    },
    "secret_values_recorded":False,
}
target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_SAFE
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user" "RUN_AS_ADMIN"; fi
for cmd in git curl python3 sha256sum openclaw; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -t 0 ] || fail_now "interactive_tty_required" "RUN_IN_INTERACTIVE_SSH_TERMINAL"
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"

PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_head" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_remote_main" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_STATUS_BEFORE" = "$EXPECTED_PRODUCT_STATUS" ] || fail_now "unexpected_product_status" "REVIEW_PRODUCT_BASELINE"

PUBLIC_BODY="$TMP_ROOT/public.body"
DIRECT_BODY="$TMP_ROOT/direct.body"
PUBLIC_STATUS="$(curl -sS -k --max-time 10 -H 'Cache-Control: no-cache' -o "$PUBLIC_BODY" -w '%{http_code}' "$OPENCLAW_URL" 2>/dev/null || true)"
DIRECT_STATUS="$(curl -sS --max-time 10 -H 'Cache-Control: no-cache' -o "$DIRECT_BODY" -w '%{http_code}' "$OPENCLAW_DIRECT" 2>/dev/null || true)"
PUBLIC_SHA="$(sha256sum "$PUBLIC_BODY" 2>/dev/null | awk '{print $1}')"
DIRECT_SHA="$(sha256sum "$DIRECT_BODY" 2>/dev/null | awk '{print $1}')"
if [ "$PUBLIC_STATUS" != "200" ] || [ "$DIRECT_STATUS" != "200" ] || [ -z "$PUBLIC_SHA" ] || [ "$PUBLIC_SHA" != "$DIRECT_SHA" ]; then
  fail_now "native_openclaw_public_preflight_failed" "RESTORE_NATIVE_OPENCLAW_MIGRATION_V2"
fi
AUTOMATED_PREFLIGHT="PASS"

capture_sessions "$BEFORE_RAW" || fail_now "sessions_before_capture_failed" "INSPECT_OPENCLAW_SESSIONS_CLI"
sanitize_sessions "$BEFORE_RAW" "$BEFORE_SAFE" || fail_now "sessions_before_sanitize_failed" "INSPECT_OPENCLAW_SESSIONS_JSON"
DASHBOARD_SESSION_COUNT_BEFORE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["dashboard_session_count"])' "$BEFORE_SAFE")"
LATENCY_SAMPLE_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["latency"]["sample_count"])' "$BEFORE_SAFE")"
LATEST_RUNTIME_MS="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["latency"]["latest_runtime_ms"]; print("unknown" if v is None else int(v))' "$BEFORE_SAFE")"
MEDIAN_RUNTIME_MS="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["latency"]["median_runtime_ms"]; print("unknown" if v is None else int(v))' "$BEFORE_SAFE")"
MAX_RUNTIME_MS="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["latency"]["max_runtime_ms"]; print("unknown" if v is None else int(v))' "$BEFORE_SAFE")"

if [ "$LATEST_RUNTIME_MS" != "unknown" ]; then
  if [ "$LATEST_RUNTIME_MS" -le 10000 ]; then LATENCY_CLASSIFICATION="GOOD";
  elif [ "$LATEST_RUNTIME_MS" -le 30000 ]; then LATENCY_CLASSIFICATION="ACCEPTABLE";
  elif [ "$LATEST_RUNTIME_MS" -le 60000 ]; then LATENCY_CLASSIFICATION="SLOW";
  else LATENCY_CLASSIFICATION="ABNORMAL_FOR_SIMPLE_ECHO"; fi
fi

printf '\n补充验收：会话级删除。\n' > /dev/tty
printf '1. 在浏览器打开：%s\n' "$SESSIONS_URL" > /dev/tty
printf '2. 在 Sessions 页面选择第二个测试对话。\n' > /dev/tty
printf '3. 点击会话行或批量操作中的 Delete；确认框应说明删除 session entry 并归档 transcript。\n' > /dev/tty
printf '4. 不要点击聊天消息旁的 Context → Delete；那不是删除对话。\n' > /dev/tty
printf '5. 删除完成后回到第一个对话，确认 ORIS_NATIVE_UI_ACCEPTED_2 仍存在。\n' > /dev/tty
printf '\n完成上述操作后输入 DONE；没有找到 Sessions 删除入口则输入 MISSING：' > /dev/tty
IFS= read -r USER_ACTION < /dev/tty

if [ "$USER_ACTION" = "DONE" ]; then
  capture_sessions "$AFTER_RAW" || fail_now "sessions_after_capture_failed" "INSPECT_OPENCLAW_SESSIONS_CLI"
  sanitize_sessions "$AFTER_RAW" "$AFTER_SAFE" || fail_now "sessions_after_sanitize_failed" "INSPECT_OPENCLAW_SESSIONS_JSON"
  python3 - "$BEFORE_SAFE" "$AFTER_SAFE" "$COMPARE_JSON" <<'PY_COMPARE'
import json,sys
from pathlib import Path
before=json.loads(Path(sys.argv[1]).read_text())
after=json.loads(Path(sys.argv[2]).read_text())
before_keys={x["key_hash"] for x in before.get("sessions",[]) if not x.get("archived")}
after_keys={x["key_hash"] for x in after.get("sessions",[]) if not x.get("archived")}
payload={
 "before_count":len(before_keys),
 "after_count":len(after_keys),
 "deleted_count":len(before_keys-after_keys),
 "retained_count":len(before_keys & after_keys),
 "new_count":len(after_keys-before_keys),
}
Path(sys.argv[3]).write_text(json.dumps(payload,indent=2)+"\n")
PY_COMPARE
  DASHBOARD_SESSION_COUNT_AFTER="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["after_count"])' "$COMPARE_JSON")"
  DELETED_SESSION_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["deleted_count"])' "$COMPARE_JSON")"
  RETAINED_SESSION_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["retained_count"])' "$COMPARE_JSON")"
  if [ "$DELETED_SESSION_COUNT" -ge 1 ] && [ "$RETAINED_SESSION_COUNT" -ge 1 ]; then
    SESSION_DELETE_VERIFIED="YES"
  fi
  printf '第一个对话及其 ORIS_NATIVE_UI_ACCEPTED_2 消息仍然存在吗？输入 y 或 n：' > /dev/tty
  IFS= read -r FIRST_ANSWER < /dev/tty
  case "$FIRST_ANSWER" in y|Y|yes|YES|Yes) FIRST_SESSION_PRESERVED="YES" ;; *) FIRST_SESSION_PRESERVED="NO" ;; esac
else
  DASHBOARD_SESSION_COUNT_AFTER="$DASHBOARD_SESSION_COUNT_BEFORE"
  DELETED_SESSION_COUNT="0"
  RETAINED_SESSION_COUNT="$DASHBOARD_SESSION_COUNT_BEFORE"
fi

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_AFTER="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
if [ "$PRODUCT_HEAD_AFTER" = "$PRODUCT_HEAD_BEFORE" ] && [ "$PRODUCT_REMOTE_AFTER" = "$PRODUCT_REMOTE_BEFORE" ] && [ "$PRODUCT_STATUS_AFTER" = "$PRODUCT_STATUS_BEFORE" ] && [ "$README_HASH_AFTER" = "$README_HASH_BEFORE" ]; then
  PRODUCT_BASELINE_PRESERVED="YES"
else
  fail_now "product_baseline_changed_during_supplemental_acceptance" "RESTORE_PRODUCT_BASELINE"
fi

if [ "$SESSION_DELETE_VERIFIED" = "YES" ] && [ "$FIRST_SESSION_PRESERVED" = "YES" ]; then
  RESULT="ACCEPTED_WITH_SUPPLEMENT"
  FINAL_ACCEPTANCE="PASS"
  NEXT_ACTION="COMPLETE_EXISTING_PRODUCT_README_GAP_RUN_TESTS_COMMIT_PUSH_AND_VERIFY_EVIDENCE"
else
  RESULT="CONDITIONAL_ACCEPTANCE"
  FINAL_ACCEPTANCE="PENDING_SESSION_DELETE"
  NEXT_ACTION="LOCATE_OR_REPAIR_SESSIONS_DELETE_UI_BEFORE_PRODUCT_README_COMPLETION"
fi

{
  echo "checked_at=$(date -Is)"
  echo "task_id=$TASK_ID"
  echo "previous_evidence=$PREVIOUS_EVIDENCE"
  echo "previous_acceptance_superseded=YES"
  echo "result=$RESULT"
  echo "session_delete_verified=$SESSION_DELETE_VERIFIED"
  echo "first_session_preserved=$FIRST_SESSION_PRESERVED"
  echo "dashboard_session_count_before=$DASHBOARD_SESSION_COUNT_BEFORE"
  echo "dashboard_session_count_after=$DASHBOARD_SESSION_COUNT_AFTER"
  echo "deleted_session_count=$DELETED_SESSION_COUNT"
  echo "retained_session_count=$RETAINED_SESSION_COUNT"
  echo "latency_sample_count=$LATENCY_SAMPLE_COUNT"
  echo "latest_runtime_ms=$LATEST_RUNTIME_MS"
  echo "median_runtime_ms=$MEDIAN_RUNTIME_MS"
  echo "max_runtime_ms=$MAX_RUNTIME_MS"
  echo "latency_classification=$LATENCY_CLASSIFICATION"
  echo "product_baseline_preserved=$PRODUCT_BASELINE_PRESERVED"
  echo "secret_values_recorded=NO"
} >> "$RUN_LOG"

export TASK_ID STAMP RESULT FAILURE_CODE PREVIOUS_EVIDENCE PREVIOUS_ACCEPTANCE_SUPERSEDED SESSION_DELETE_VERIFIED FIRST_SESSION_PRESERVED DASHBOARD_SESSION_COUNT_BEFORE DASHBOARD_SESSION_COUNT_AFTER DELETED_SESSION_COUNT RETAINED_SESSION_COUNT LATENCY_SAMPLE_COUNT LATEST_RUNTIME_MS MEDIAN_RUNTIME_MS MAX_RUNTIME_MS LATENCY_CLASSIFICATION PRODUCT_BASELINE_PRESERVED FINAL_ACCEPTANCE NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$BEFORE_SAFE" "$COMPARE_JSON" "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path
before=json.loads(Path(sys.argv[1]).read_text())
compare=None
if Path(sys.argv[2]).exists(): compare=json.loads(Path(sys.argv[2]).read_text())
payload={
 "task_id":os.environ.get("TASK_ID"),
 "checked_at":os.environ.get("STAMP"),
 "result":os.environ.get("RESULT"),
 "failure_code":os.environ.get("FAILURE_CODE"),
 "correction":{"supersedes":os.environ.get("PREVIOUS_EVIDENCE"),"reason":"User clarified that session delete/archive was not actually tested; Context delete was clicked instead.","previous_acceptance_superseded":True},
 "supplemental_checks":{"session_delete_verified":os.environ.get("SESSION_DELETE_VERIFIED")=="YES","first_session_preserved":os.environ.get("FIRST_SESSION_PRESERVED")=="YES","comparison":compare},
 "latency":{"samples":before.get("latency"),"latest_classification":os.environ.get("LATENCY_CLASSIFICATION"),"thresholds_ms":{"good_max":10000,"acceptable_max":30000,"slow_max":60000},"threshold_basis":"Commercial UX engineering thresholds for a simple exact-echo prompt, not an OpenClaw vendor SLA."},
 "final_acceptance":os.environ.get("FINAL_ACCEPTANCE"),
 "safety":{"product_baseline_preserved":os.environ.get("PRODUCT_BASELINE_PRESERVED")=="YES","current_task_updated":False,"product_task_submitted":False,"product_repository_mutated":False,"openclaw_config_mutated":False,"secret_values_recorded":False},
 "next_action":os.environ.get("NEXT_ACTION"),
 "evidence":{"log_path":os.environ.get("EVIDENCE_LOG_REL"),"json_path":os.environ.get("EVIDENCE_JSON_REL"),"self_commit_sha_omitted_to_prevent_post_commit_log_drift":True}
}
Path(sys.argv[3]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_RESULT

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
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native OpenClaw supplemental acceptance $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"; fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then EVIDENCE_REMOTE_VERIFIED="YES"; else RESULT="FAILED"; FAILURE_CODE="evidence_remote_sha_mismatch"; NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"; fi

summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
