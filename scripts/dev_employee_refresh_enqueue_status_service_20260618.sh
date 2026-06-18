#!/usr/bin/env bash

TASK_ID="commercial-openclaw-native-plugin-validation-20260618"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
SERVICE="oris-dev-employee-enqueue.service"
OPENCLAW_SERVICE="openclaw-gateway.service"
SERVER_REL="scripts/dev_employee_enqueue_server.py"
SERVER_PATH="$ORIS_REPO/$SERVER_REL"
EXPECTED_PRODUCT_COMMIT="bcb93e17ea88704548101f5e4a5c460e15a80ec7"
PORT="18891"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-enqueue-status-refresh-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/refresh.log"
RESULT_JSON="$TMP_ROOT/refresh.json"
ORIGIN_SERVER="$TMP_ROOT/origin-server.py"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_native_plugin_validation"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/enqueue-status-service-refresh-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/enqueue-status-service-refresh-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
SERVICE_STATE_BEFORE="unknown"
SERVICE_STATE_AFTER="unknown"
MAIN_PID_BEFORE="unknown"
MAIN_PID_AFTER="unknown"
PROCESS_USES_AUTHORITY_SCRIPT="NO"
SERVER_MATCHES_ORIGIN_MAIN="NO"
LATEST_STATUS_BEFORE="000"
LATEST_STATUS_AFTER="000"
HEALTH_STATUS_AFTER="000"
QUEUE_STATUS_AFTER="000"
SERVICE_RESTARTED="NO"
LISTENER_LOOPBACK_ONLY="unknown"
QUEUE_STATE_UNCHANGED="NO"
ORIS_WORKTREE_PRESERVED="NO"
PRODUCT_BASELINE_PRESERVED="NO"
OPENCLAW_PID_UNCHANGED="NO"
CONFIG_CHANGED="NO"
PRODUCT_TASK_SUBMITTED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_ENQUEUE_STATUS_SERVICE_REFRESH_FAILURE"

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
  echo "SERVICE=$SERVICE"
  echo "SERVICE_STATE_BEFORE=$SERVICE_STATE_BEFORE"
  echo "SERVICE_STATE_AFTER=$SERVICE_STATE_AFTER"
  echo "MAIN_PID_BEFORE=$MAIN_PID_BEFORE"
  echo "MAIN_PID_AFTER=$MAIN_PID_AFTER"
  echo "PROCESS_USES_AUTHORITY_SCRIPT=$PROCESS_USES_AUTHORITY_SCRIPT"
  echo "SERVER_MATCHES_ORIGIN_MAIN=$SERVER_MATCHES_ORIGIN_MAIN"
  echo "LATEST_STATUS_BEFORE=$LATEST_STATUS_BEFORE"
  echo "LATEST_STATUS_AFTER=$LATEST_STATUS_AFTER"
  echo "HEALTH_STATUS_AFTER=$HEALTH_STATUS_AFTER"
  echo "QUEUE_STATUS_AFTER=$QUEUE_STATUS_AFTER"
  echo "SERVICE_RESTARTED=$SERVICE_RESTARTED"
  echo "LISTENER_LOOPBACK_ONLY=$LISTENER_LOOPBACK_ONLY"
  echo "QUEUE_STATE_UNCHANGED=$QUEUE_STATE_UNCHANGED"
  echo "ORIS_WORKTREE_PRESERVED=$ORIS_WORKTREE_PRESERVED"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "OPENCLAW_PID_UNCHANGED=$OPENCLAW_PID_UNCHANGED"
  echo "CONFIG_CHANGED=$CONFIG_CHANGED"
  echo "PRODUCT_TASK_SUBMITTED=$PRODUCT_TASK_SUBMITTED"
  echo "SECRET_SCAN=$SECRET_SCAN"
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

queue_fingerprint() {
  python3 - "$ORIS_REPO/orchestration/dev_employee_queue" <<'PY_QUEUE'
import hashlib,sys
from pathlib import Path
root=Path(sys.argv[1]); rows=[]
if root.exists():
    for path in sorted(root.glob('*.json')):
        try:
            s=path.stat(); rows.append(f"{path.name}\t{s.st_size}\t{s.st_mtime_ns}")
        except FileNotFoundError:
            pass
print(hashlib.sha256('\n'.join(rows).encode()).hexdigest())
PY_QUEUE
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user" "RUN_AS_ADMIN"; fi
for cmd in git curl python3 sha256sum systemctl ss grep awk tr; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$SERVER_PATH" ] || fail_now "authority_server_script_missing" "RESTORE_ORIS_SERVER_SCRIPT"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=CONTROLLED_ENQUEUE_STATUS_SERVICE_REFRESH"
log "SERVER_REL=$SERVER_REL"
log "CONFIG_CHANGED=NO"
log "PRODUCT_TASK_SUBMITTED=NO"
log "OPENCLAW_SERVICE_RESTARTED=NO"
log "PRODUCT_REPOSITORY_MUTATED=NO"
log "SECRET_VALUES_RECORDED=NO"

ACTIVE_QUEUE_COUNT="$(find "$ORIS_REPO/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' -o -name '*.claimed.json' -o -name '*.planning.json' -o -name '*.executing.json' -o -name '*.committing.json' -o -name '*.pushing.json' -o -name '*.cancelling.json' \) 2>/dev/null | wc -l | tr -d ' ')"
log "ACTIVE_QUEUE_COUNT=$ACTIVE_QUEUE_COUNT"
[ "$ACTIVE_QUEUE_COUNT" = "0" ] || fail_now "active_queue_present" "WAIT_FOR_QUEUE_TO_DRAIN"

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" show "origin/main:$SERVER_REL" > "$ORIGIN_SERVER" 2>> "$RUN_LOG" || fail_now "origin_server_script_unreadable" "RESTORE_SERVER_SCRIPT_ON_MAIN"
LOCAL_SERVER_SHA="$(sha256sum "$SERVER_PATH" | awk '{print $1}')"
ORIGIN_SERVER_SHA="$(sha256sum "$ORIGIN_SERVER" | awk '{print $1}')"
if [ "$LOCAL_SERVER_SHA" = "$ORIGIN_SERVER_SHA" ]; then SERVER_MATCHES_ORIGIN_MAIN="YES"; fi
[ "$SERVER_MATCHES_ORIGIN_MAIN" = "YES" ] || fail_now "local_server_differs_from_origin_main" "PRESERVE_AND_REVIEW_LOCAL_SERVER_SCRIPT"

grep -q 'if path == "/latest"' "$SERVER_PATH" || fail_now "authority_server_missing_latest_route" "REPAIR_SERVER_ROUTE_ON_GITHUB"

ORIS_STATUS_BEFORE_FILE="$TMP_ROOT/oris-status-before.bin"
ORIS_STATUS_AFTER_FILE="$TMP_ROOT/oris-status-after.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_BEFORE_FILE" || fail_now "oris_status_capture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_BEFORE_SHA="$(sha256sum "$ORIS_STATUS_BEFORE_FILE" | awk '{print $1}')"
QUEUE_FINGERPRINT_BEFORE="$(queue_fingerprint)"
PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
OPENCLAW_PID_BEFORE="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"

[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_head" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_remote_main" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ -z "$PRODUCT_STATUS_BEFORE" ] || fail_now "product_worktree_not_clean" "RESTORE_COMPLETED_PRODUCT_BASELINE"

SERVICE_STATE_BEFORE="$(systemctl --user is-active "$SERVICE" 2>/dev/null || true)"
MAIN_PID_BEFORE="$(systemctl --user show "$SERVICE" -p MainPID --value 2>/dev/null || true)"
[ "$SERVICE_STATE_BEFORE" = "active" ] || fail_now "enqueue_service_not_active" "INSPECT_ENQUEUE_SERVICE"
case "$MAIN_PID_BEFORE" in ''|0|*[!0-9]*) fail_now "enqueue_service_main_pid_invalid" "INSPECT_ENQUEUE_SERVICE" ;; esac

CMDLINE_FILE="$TMP_ROOT/cmdline.txt"
tr '\0' '\n' < "/proc/$MAIN_PID_BEFORE/cmdline" > "$CMDLINE_FILE" 2>/dev/null || fail_now "enqueue_process_cmdline_unreadable" "INSPECT_ENQUEUE_SERVICE_PROCESS"
if grep -Fqx "$SERVER_PATH" "$CMDLINE_FILE"; then PROCESS_USES_AUTHORITY_SCRIPT="YES"; fi
[ "$PROCESS_USES_AUTHORITY_SCRIPT" = "YES" ] || fail_now "enqueue_process_not_using_authority_script" "INSPECT_SYSTEMD_EXECSTART_BEFORE_RESTART"

LATEST_STATUS_BEFORE="$(curl -sS --max-time 8 -o "$TMP_ROOT/latest-before.json" -w '%{http_code}' "http://127.0.0.1:$PORT/latest" 2>/dev/null || true)"
log "LATEST_STATUS_BEFORE=$LATEST_STATUS_BEFORE"

if [ "$LATEST_STATUS_BEFORE" = "200" ]; then
  SERVICE_RESTARTED="NO"
else
  if systemctl --user restart "$SERVICE" >> "$RUN_LOG" 2>&1; then
    SERVICE_RESTARTED="YES"
  else
    fail_now "enqueue_service_restart_failed" "INSPECT_ENQUEUE_SERVICE_JOURNAL"
  fi
fi

for attempt in 1 2 3 4 5 6 7 8 9 10; do
  SERVICE_STATE_AFTER="$(systemctl --user is-active "$SERVICE" 2>/dev/null || true)"
  MAIN_PID_AFTER="$(systemctl --user show "$SERVICE" -p MainPID --value 2>/dev/null || true)"
  HEALTH_STATUS_AFTER="$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/health" 2>/dev/null || true)"
  QUEUE_STATUS_AFTER="$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/queue" 2>/dev/null || true)"
  LATEST_STATUS_AFTER="$(curl -sS --max-time 5 -o "$TMP_ROOT/latest-after.json" -w '%{http_code}' "http://127.0.0.1:$PORT/latest" 2>/dev/null || true)"
  if [ "$SERVICE_STATE_AFTER" = "active" ] && [ "$HEALTH_STATUS_AFTER" = "200" ] && [ "$QUEUE_STATUS_AFTER" = "200" ] && [ "$LATEST_STATUS_AFTER" = "200" ]; then
    break
  fi
  sleep 1
done

[ "$SERVICE_STATE_AFTER" = "active" ] || fail_now "enqueue_service_not_active_after_refresh" "INSPECT_ENQUEUE_SERVICE_JOURNAL"
[ "$HEALTH_STATUS_AFTER" = "200" ] || fail_now "enqueue_health_unhealthy_after_refresh" "INSPECT_ENQUEUE_SERVICE_JOURNAL"
[ "$QUEUE_STATUS_AFTER" = "200" ] || fail_now "enqueue_queue_unhealthy_after_refresh" "INSPECT_ENQUEUE_SERVICE_JOURNAL"
[ "$LATEST_STATUS_AFTER" = "200" ] || fail_now "enqueue_latest_still_unavailable_after_refresh" "INSPECT_RUNNING_SERVER_VERSION_AND_SERVICE_UNIT"

LISTENER="$(ss -ltn 2>/dev/null | awk -v p=":$PORT" '$4 ~ p"$" {print $4; exit}')"
case "$LISTENER" in 127.0.0.1:*|\[::1\]:*) LISTENER_LOOPBACK_ONLY="YES" ;; *) LISTENER_LOOPBACK_ONLY="NO" ;; esac
[ "$LISTENER_LOOPBACK_ONLY" = "YES" ] || fail_now "enqueue_listener_not_loopback_only" "RESTORE_PRIVATE_ENQUEUE_BINDING"

QUEUE_FINGERPRINT_AFTER="$(queue_fingerprint)"
[ "$QUEUE_FINGERPRINT_BEFORE" = "$QUEUE_FINGERPRINT_AFTER" ] && QUEUE_STATE_UNCHANGED="YES"
[ "$QUEUE_STATE_UNCHANGED" = "YES" ] || fail_now "queue_changed_during_service_refresh" "INSPECT_UNEXPECTED_QUEUE_MUTATION"

OPENCLAW_PID_AFTER="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"
[ "$OPENCLAW_PID_BEFORE" = "$OPENCLAW_PID_AFTER" ] && OPENCLAW_PID_UNCHANGED="YES"
[ "$OPENCLAW_PID_UNCHANGED" = "YES" ] || fail_now "openclaw_service_changed_during_refresh" "INSPECT_UNEXPECTED_OPENCLAW_CHANGE"

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
if [ "$PRODUCT_HEAD_BEFORE" = "$PRODUCT_HEAD_AFTER" ] && [ "$PRODUCT_REMOTE_BEFORE" = "$PRODUCT_REMOTE_AFTER" ] && [ "$PRODUCT_STATUS_BEFORE" = "$PRODUCT_STATUS_AFTER" ] && [ "$PRODUCT_TREE_BEFORE" = "$PRODUCT_TREE_AFTER" ]; then
  PRODUCT_BASELINE_PRESERVED="YES"
fi
[ "$PRODUCT_BASELINE_PRESERVED" = "YES" ] || fail_now "product_baseline_changed_during_refresh" "RESTORE_COMPLETED_PRODUCT_BASELINE"

git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_AFTER_FILE" || fail_now "oris_status_recapture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_AFTER_SHA="$(sha256sum "$ORIS_STATUS_AFTER_FILE" | awk '{print $1}')"
[ "$ORIS_STATUS_BEFORE_SHA" = "$ORIS_STATUS_AFTER_SHA" ] && ORIS_WORKTREE_PRESERVED="YES"
[ "$ORIS_WORKTREE_PRESERVED" = "YES" ] || fail_now "oris_worktree_changed_during_refresh" "INSPECT_UNEXPECTED_ORIS_WORKTREE_CHANGE"

RESULT="REFRESHED"
NEXT_ACTION="RERUN_NATIVE_PLUGIN_VALIDATION_V3"

export TASK_ID STAMP RESULT FAILURE_CODE SERVICE SERVICE_STATE_BEFORE SERVICE_STATE_AFTER MAIN_PID_BEFORE MAIN_PID_AFTER PROCESS_USES_AUTHORITY_SCRIPT SERVER_MATCHES_ORIGIN_MAIN LATEST_STATUS_BEFORE LATEST_STATUS_AFTER HEALTH_STATUS_AFTER QUEUE_STATUS_AFTER SERVICE_RESTARTED LISTENER_LOOPBACK_ONLY QUEUE_STATE_UNCHANGED ORIS_WORKTREE_PRESERVED PRODUCT_BASELINE_PRESERVED OPENCLAW_PID_UNCHANGED CONFIG_CHANGED PRODUCT_TASK_SUBMITTED NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path
payload={
  "task_id":os.environ["TASK_ID"],
  "checked_at":os.environ["STAMP"],
  "result":os.environ["RESULT"],
  "failure_code":os.environ.get("FAILURE_CODE") or None,
  "service":{
    "name":os.environ["SERVICE"],
    "state_before":os.environ["SERVICE_STATE_BEFORE"],
    "state_after":os.environ["SERVICE_STATE_AFTER"],
    "main_pid_before":os.environ["MAIN_PID_BEFORE"],
    "main_pid_after":os.environ["MAIN_PID_AFTER"],
    "process_uses_authority_script":os.environ["PROCESS_USES_AUTHORITY_SCRIPT"]=="YES",
    "server_matches_origin_main":os.environ["SERVER_MATCHES_ORIGIN_MAIN"]=="YES",
    "restarted":os.environ["SERVICE_RESTARTED"]=="YES",
    "listener_loopback_only":os.environ["LISTENER_LOOPBACK_ONLY"]=="YES"
  },
  "routes":{
    "latest_before":os.environ["LATEST_STATUS_BEFORE"],
    "latest_after":os.environ["LATEST_STATUS_AFTER"],
    "health_after":os.environ["HEALTH_STATUS_AFTER"],
    "queue_after":os.environ["QUEUE_STATUS_AFTER"]
  },
  "safety":{
    "queue_state_unchanged":os.environ["QUEUE_STATE_UNCHANGED"]=="YES",
    "oris_worktree_preserved":os.environ["ORIS_WORKTREE_PRESERVED"]=="YES",
    "product_baseline_preserved":os.environ["PRODUCT_BASELINE_PRESERVED"]=="YES",
    "openclaw_pid_unchanged":os.environ["OPENCLAW_PID_UNCHANGED"]=="YES",
    "config_changed":False,
    "product_task_submitted":False,
    "secret_values_recorded":False
  },
  "next_action":os.environ["NEXT_ACTION"],
  "evidence":{
    "log_path":os.environ["EVIDENCE_LOG_REL"],
    "json_path":os.environ["EVIDENCE_JSON_REL"],
    "self_commit_sha_omitted_to_prevent_post_commit_log_drift":True
  }
}
Path(sys.argv[1]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_RESULT

{
  echo "checked_at=$(date -Is)"
  echo "task_id=$TASK_ID"
  echo "result=$RESULT"
  echo "service=$SERVICE"
  echo "service_state_before=$SERVICE_STATE_BEFORE"
  echo "service_state_after=$SERVICE_STATE_AFTER"
  echo "process_uses_authority_script=$PROCESS_USES_AUTHORITY_SCRIPT"
  echo "server_matches_origin_main=$SERVER_MATCHES_ORIGIN_MAIN"
  echo "latest_status_before=$LATEST_STATUS_BEFORE"
  echo "latest_status_after=$LATEST_STATUS_AFTER"
  echo "health_status_after=$HEALTH_STATUS_AFTER"
  echo "queue_status_after=$QUEUE_STATUS_AFTER"
  echo "service_restarted=$SERVICE_RESTARTED"
  echo "listener_loopback_only=$LISTENER_LOOPBACK_ONLY"
  echo "queue_state_unchanged=$QUEUE_STATE_UNCHANGED"
  echo "oris_worktree_preserved=$ORIS_WORKTREE_PRESERVED"
  echo "product_baseline_preserved=$PRODUCT_BASELINE_PRESERVED"
  echo "openclaw_pid_unchanged=$OPENCLAW_PID_UNCHANGED"
  echo "config_changed=NO"
  echo "product_task_submitted=NO"
  echo "secret_values_recorded=NO"
} >> "$RUN_LOG"

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY_SCAN'
import re,sys
from pathlib import Path
patterns=[
 re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
 re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),
 re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),
 re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
 re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b')
]
for filename in sys.argv[1:]:
    text=Path(filename).read_text(encoding='utf-8',errors='replace')
    if any(pattern.search(text) for pattern in patterns): raise SystemExit(1)
PY_SCAN
if [ "$?" -eq 0 ]; then SECRET_SCAN="PASS"; else fail_now "refresh_evidence_secret_scan_failed" "REPAIR_REFRESH_EVIDENCE_REDACTION"; fi

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "evidence_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL" || fail_now "evidence_directory_create_failed" "CHECK_EVIDENCE_WORKTREE_PERMISSIONS"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_COPY'
import json,sys
from pathlib import Path
sl,dl,sj,dj=map(Path,sys.argv[1:])
dl.write_text('\n'.join(line.rstrip(' \t\r') for line in sl.read_text(encoding='utf-8',errors='replace').splitlines())+'\n',encoding='utf-8')
dj.write_text(json.dumps(json.loads(sj.read_text(encoding='utf-8')),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_COPY
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record enqueue status service refresh $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then EVIDENCE_REMOTE_VERIFIED="YES"; else fail_now "evidence_remote_sha_mismatch" "VERIFY_ORIS_REMOTE_MAIN"; fi

summary
exit 0
