#!/usr/bin/env bash

TASK_ID="commercial-openclaw-native-plugin-install-20260618"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_SERVICE="openclaw-gateway.service"
PLUGIN_ID="oris-dev-employee"
MARKER_FILE="$HOME/.openclaw/private/oris-dev-employee-plugin-install-current.json"
EXPECTED_PRODUCT_COMMIT="bcb93e17ea88704548101f5e4a5c460e15a80ec7"
DOMAIN="control.orisfy.com"
OPENCLAW_PORT="18789"
ENQUEUE_PORT="18891"
INTAKE_PORT="18892"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-plugin-rollback-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/rollback.log"
RESULT_JSON="$TMP_ROOT/rollback.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_native_plugin_install"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/openclaw-native-plugin-rollback-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/openclaw-native-plugin-rollback-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
BACKUP_FILE=""
PLUGIN_PRESENT_BEFORE="unknown"
PLUGIN_PRESENT_AFTER="unknown"
UNINSTALL_RC="not_run"
CONFIG_RESTORED="NO"
SERVICE_RESTART="NOT_RUN"
SERVICE_STATE="unknown"
DIRECT_ROOT_STATUS="000"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ROOT_MATCHES_DIRECT="NO"
ENQUEUE_LOOPBACK_ONLY="unknown"
INTAKE_LOOPBACK_ONLY="unknown"
QUEUE_STATE_UNCHANGED="NO"
ORIS_WORKTREE_PRESERVED="NO"
PRODUCT_BASELINE_PRESERVED="NO"
MARKER_ARCHIVED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_NATIVE_PLUGIN_ROLLBACK_FAILURE"

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
  echo "PLUGIN_ID=$PLUGIN_ID"
  echo "PLUGIN_PRESENT_BEFORE=$PLUGIN_PRESENT_BEFORE"
  echo "PLUGIN_PRESENT_AFTER=$PLUGIN_PRESENT_AFTER"
  echo "UNINSTALL_RC=$UNINSTALL_RC"
  echo "CONFIG_RESTORED=$CONFIG_RESTORED"
  echo "SERVICE_RESTART=$SERVICE_RESTART"
  echo "SERVICE_STATE=$SERVICE_STATE"
  echo "DIRECT_ROOT_STATUS=$DIRECT_ROOT_STATUS"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ROOT_MATCHES_DIRECT=$PUBLIC_ROOT_MATCHES_DIRECT"
  echo "ENQUEUE_LOOPBACK_ONLY=$ENQUEUE_LOOPBACK_ONLY"
  echo "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
  echo "QUEUE_STATE_UNCHANGED=$QUEUE_STATE_UNCHANGED"
  echo "ORIS_WORKTREE_PRESERVED=$ORIS_WORKTREE_PRESERVED"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "MARKER_ARCHIVED=$MARKER_ARCHIVED"
  echo "BACKUP_FILE=$BACKUP_FILE"
  echo "SECRET_SCAN=$SECRET_SCAN"
  echo "EVIDENCE_LOG=$EVIDENCE_LOG_REL"
  echo "EVIDENCE_JSON=$EVIDENCE_JSON_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "OPENCLAW_REINSTALLED_OR_UPGRADED=NO"
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

plugin_present() {
  local output="$1"
  openclaw plugins list --json > "$output" 2>> "$RUN_LOG"
  if [ "$?" -ne 0 ]; then
    echo "unknown"
    return
  fi
  python3 - "$output" "$PLUGIN_ID" <<'PY_PLUGIN'
import json,sys
from pathlib import Path
try:
    data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
except Exception:
    print('unknown'); raise SystemExit(0)
plugins=data.get('plugins') if isinstance(data,dict) else []
found=False
if isinstance(plugins,list):
    for item in plugins:
        if isinstance(item,dict) and str(item.get('id') or item.get('name') or '')==sys.argv[2]:
            found=True; break
print('YES' if found else 'NO')
PY_PLUGIN
}

loopback_only() {
  local port="$1"
  local listener
  listener="$(ss -ltn 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" {print $4; exit}')"
  case "$listener" in
    127.0.0.1:*|\[::1\]:*) echo "YES" ;;
    *) echo "NO" ;;
  esac
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user" "RUN_AS_ADMIN"; fi
for cmd in git openclaw python3 sha256sum systemctl curl ss cp chmod mv stat find awk; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$MARKER_FILE" ] || fail_now "plugin_install_marker_missing" "INSPECT_PRIVATE_PLUGIN_INSTALL_STATE"
[ "$(stat -c '%a' "$MARKER_FILE" 2>/dev/null)" = "600" ] || fail_now "plugin_install_marker_not_0600" "RESTORE_PRIVATE_MARKER_PERMISSIONS"

BACKUP_FILE="$(python3 - "$MARKER_FILE" "$PLUGIN_ID" <<'PY_MARKER'
import json,sys
from pathlib import Path
data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if data.get('plugin_id')!=sys.argv[2]:
    raise SystemExit(2)
backup=data.get('config_backup')
if not isinstance(backup,str) or not backup:
    raise SystemExit(3)
print(backup)
PY_MARKER
)"
[ "$?" -eq 0 ] && [ -n "$BACKUP_FILE" ] || fail_now "plugin_install_marker_invalid" "INSPECT_PRIVATE_PLUGIN_INSTALL_STATE"
[ -f "$BACKUP_FILE" ] || fail_now "preinstall_config_backup_missing" "RESTORE_PREINSTALL_CONFIG_BACKUP"
[ "$(stat -c '%a' "$BACKUP_FILE" 2>/dev/null)" = "600" ] || fail_now "preinstall_config_backup_not_0600" "RESTORE_BACKUP_PERMISSIONS"
python3 -m json.tool "$BACKUP_FILE" >/dev/null 2>&1 || fail_now "preinstall_config_backup_invalid_json" "RESTORE_VALID_PREINSTALL_CONFIG"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=REVERSIBLE_NATIVE_PLUGIN_ROLLBACK"
log "PLUGIN_ID=$PLUGIN_ID"
log "BACKUP_FILE=$BACKUP_FILE"
log "PRODUCT_TASK_SUBMITTED=NO"
log "OPENCLAW_REINSTALLED_OR_UPGRADED=NO"
log "SECRET_VALUES_RECORDED=NO"

ACTIVE_QUEUE_COUNT="$(find "$ORIS_REPO/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' -o -name '*.claimed.json' -o -name '*.planning.json' -o -name '*.executing.json' -o -name '*.committing.json' -o -name '*.pushing.json' -o -name '*.cancelling.json' \) 2>/dev/null | wc -l | tr -d ' ')"
[ "$ACTIVE_QUEUE_COUNT" = "0" ] || fail_now "active_queue_present" "WAIT_FOR_QUEUE_TO_DRAIN"

ORIS_STATUS_BEFORE_FILE="$TMP_ROOT/oris-status-before.bin"
ORIS_STATUS_AFTER_FILE="$TMP_ROOT/oris-status-after.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_BEFORE_FILE" || fail_now "oris_status_capture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_BEFORE_SHA="$(sha256sum "$ORIS_STATUS_BEFORE_FILE" | awk '{print $1}')"
QUEUE_BEFORE="$(queue_fingerprint)"
PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_head" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_remote_main" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ -z "$PRODUCT_STATUS_BEFORE" ] || fail_now "product_worktree_not_clean" "RESTORE_COMPLETED_PRODUCT_BASELINE"

PLUGIN_PRESENT_BEFORE="$(plugin_present "$TMP_ROOT/plugins-before.json")"
if [ "$PLUGIN_PRESENT_BEFORE" = "YES" ]; then
  openclaw plugins uninstall "$PLUGIN_ID" >> "$RUN_LOG" 2>&1
  UNINSTALL_RC="$?"
  [ "$UNINSTALL_RC" = "0" ] || fail_now "plugin_uninstall_failed" "INSPECT_OPENCLAW_PLUGIN_UNINSTALL"
else
  UNINSTALL_RC="not_needed"
fi

cp "$BACKUP_FILE" "$OPENCLAW_CONFIG" >> "$RUN_LOG" 2>&1 || fail_now "config_restore_copy_failed" "CHECK_OPENCLAW_CONFIG_PERMISSIONS"
chmod 600 "$OPENCLAW_CONFIG" >> "$RUN_LOG" 2>&1 || fail_now "config_restore_permission_failed" "CHECK_OPENCLAW_CONFIG_PERMISSIONS"
CONFIG_RESTORED="YES"

if systemctl --user restart "$OPENCLAW_SERVICE" >> "$RUN_LOG" 2>&1; then
  SERVICE_RESTART="PASS"
else
  SERVICE_RESTART="FAIL"
  fail_now "openclaw_gateway_restart_failed" "INSPECT_OPENCLAW_GATEWAY_JOURNAL"
fi

for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  SERVICE_STATE="$(systemctl --user is-active "$OPENCLAW_SERVICE" 2>/dev/null || true)"
  DIRECT_ROOT_STATUS="$(curl -sS --max-time 5 -o "$TMP_ROOT/direct.body" -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
  PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 5 -H 'Cache-Control: no-cache' -o "$TMP_ROOT/public.body" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
  if [ "$SERVICE_STATE" = "active" ] && [ "$DIRECT_ROOT_STATUS" = "200" ] && [ "$PUBLIC_ROOT_STATUS" = "200" ]; then
    break
  fi
  sleep 1
done
[ "$SERVICE_STATE" = "active" ] || fail_now "openclaw_gateway_not_active_after_rollback" "INSPECT_OPENCLAW_GATEWAY_JOURNAL"
[ "$DIRECT_ROOT_STATUS" = "200" ] || fail_now "direct_root_unhealthy_after_rollback" "INSPECT_OPENCLAW_GATEWAY_JOURNAL"
[ "$PUBLIC_ROOT_STATUS" = "200" ] || fail_now "public_root_unhealthy_after_rollback" "INSPECT_PUBLIC_ROUTING"
DIRECT_SHA="$(sha256sum "$TMP_ROOT/direct.body" 2>/dev/null | awk '{print $1}')"
PUBLIC_SHA="$(sha256sum "$TMP_ROOT/public.body" 2>/dev/null | awk '{print $1}')"
if [ -n "$DIRECT_SHA" ] && [ "$DIRECT_SHA" = "$PUBLIC_SHA" ]; then PUBLIC_ROOT_MATCHES_DIRECT="YES"; fi
[ "$PUBLIC_ROOT_MATCHES_DIRECT" = "YES" ] || fail_now "public_root_no_longer_matches_direct" "INSPECT_PUBLIC_ROUTING"

PLUGIN_PRESENT_AFTER="$(plugin_present "$TMP_ROOT/plugins-after.json")"
[ "$PLUGIN_PRESENT_AFTER" = "NO" ] || fail_now "plugin_still_present_after_rollback" "INSPECT_OPENCLAW_PLUGIN_REGISTRY"

ENQUEUE_LOOPBACK_ONLY="$(loopback_only "$ENQUEUE_PORT")"
INTAKE_LOOPBACK_ONLY="$(loopback_only "$INTAKE_PORT")"
[ "$ENQUEUE_LOOPBACK_ONLY" = "YES" ] || fail_now "enqueue_listener_not_loopback_only" "RESTORE_PRIVATE_ENQUEUE_BINDING"
[ "$INTAKE_LOOPBACK_ONLY" = "YES" ] || fail_now "intake_listener_not_loopback_only" "RESTORE_PRIVATE_INTAKE_BINDING"

QUEUE_AFTER="$(queue_fingerprint)"
[ "$QUEUE_BEFORE" = "$QUEUE_AFTER" ] && QUEUE_STATE_UNCHANGED="YES"
[ "$QUEUE_STATE_UNCHANGED" = "YES" ] || fail_now "queue_changed_during_rollback" "INSPECT_UNEXPECTED_QUEUE_MUTATION"

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
if [ "$PRODUCT_HEAD_BEFORE" = "$PRODUCT_HEAD_AFTER" ] && [ "$PRODUCT_REMOTE_BEFORE" = "$PRODUCT_REMOTE_AFTER" ] && [ "$PRODUCT_STATUS_BEFORE" = "$PRODUCT_STATUS_AFTER" ] && [ "$PRODUCT_TREE_BEFORE" = "$PRODUCT_TREE_AFTER" ]; then PRODUCT_BASELINE_PRESERVED="YES"; fi
[ "$PRODUCT_BASELINE_PRESERVED" = "YES" ] || fail_now "product_baseline_changed_during_rollback" "RESTORE_COMPLETED_PRODUCT_BASELINE"

git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_AFTER_FILE" || fail_now "oris_status_recapture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_AFTER_SHA="$(sha256sum "$ORIS_STATUS_AFTER_FILE" | awk '{print $1}')"
[ "$ORIS_STATUS_BEFORE_SHA" = "$ORIS_STATUS_AFTER_SHA" ] && ORIS_WORKTREE_PRESERVED="YES"
[ "$ORIS_WORKTREE_PRESERVED" = "YES" ] || fail_now "oris_worktree_changed_during_rollback" "INSPECT_UNEXPECTED_ORIS_WORKTREE_CHANGE"

ARCHIVED_MARKER="$HOME/.openclaw/private/oris-dev-employee-plugin-install-rolled-back-$STAMP.json"
mv "$MARKER_FILE" "$ARCHIVED_MARKER" >> "$RUN_LOG" 2>&1 || fail_now "plugin_marker_archive_failed" "INSPECT_PRIVATE_MARKER_PERMISSIONS"
chmod 600 "$ARCHIVED_MARKER" >> "$RUN_LOG" 2>&1 || fail_now "plugin_marker_archive_permission_failed" "INSPECT_PRIVATE_MARKER_PERMISSIONS"
MARKER_ARCHIVED="YES"

RESULT="ROLLED_BACK"
NEXT_ACTION="REVIEW_ROLLBACK_EVIDENCE_BEFORE_ANY_REINSTALL"

export TASK_ID STAMP RESULT FAILURE_CODE PLUGIN_ID PLUGIN_PRESENT_BEFORE PLUGIN_PRESENT_AFTER UNINSTALL_RC CONFIG_RESTORED SERVICE_RESTART SERVICE_STATE DIRECT_ROOT_STATUS PUBLIC_ROOT_STATUS PUBLIC_ROOT_MATCHES_DIRECT ENQUEUE_LOOPBACK_ONLY INTAKE_LOOPBACK_ONLY QUEUE_STATE_UNCHANGED ORIS_WORKTREE_PRESERVED PRODUCT_BASELINE_PRESERVED MARKER_ARCHIVED BACKUP_FILE NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path
payload={
  'task_id':os.environ['TASK_ID'],
  'checked_at':os.environ['STAMP'],
  'result':os.environ['RESULT'],
  'failure_code':os.environ.get('FAILURE_CODE') or None,
  'plugin':{
    'id':os.environ['PLUGIN_ID'],
    'present_before':os.environ['PLUGIN_PRESENT_BEFORE'],
    'present_after':os.environ['PLUGIN_PRESENT_AFTER'],
    'uninstall_rc':os.environ['UNINSTALL_RC'],
  },
  'config':{
    'restored':os.environ['CONFIG_RESTORED']=='YES',
    'backup_file':os.environ['BACKUP_FILE'],
  },
  'gateway':{
    'restart':os.environ['SERVICE_RESTART'],
    'state':os.environ['SERVICE_STATE'],
    'direct_root_status':os.environ['DIRECT_ROOT_STATUS'],
    'public_root_status':os.environ['PUBLIC_ROOT_STATUS'],
    'public_matches_direct':os.environ['PUBLIC_ROOT_MATCHES_DIRECT']=='YES',
  },
  'safety':{
    'enqueue_loopback_only':os.environ['ENQUEUE_LOOPBACK_ONLY']=='YES',
    'intake_loopback_only':os.environ['INTAKE_LOOPBACK_ONLY']=='YES',
    'queue_state_unchanged':os.environ['QUEUE_STATE_UNCHANGED']=='YES',
    'oris_worktree_preserved':os.environ['ORIS_WORKTREE_PRESERVED']=='YES',
    'product_baseline_preserved':os.environ['PRODUCT_BASELINE_PRESERVED']=='YES',
    'marker_archived':os.environ['MARKER_ARCHIVED']=='YES',
    'product_task_submitted':False,
    'openclaw_reinstalled_or_upgraded':False,
    'secret_values_recorded':False,
  },
  'next_action':os.environ['NEXT_ACTION'],
  'evidence':{
    'log_path':os.environ['EVIDENCE_LOG_REL'],
    'json_path':os.environ['EVIDENCE_JSON_REL'],
    'self_commit_sha_omitted_to_prevent_post_commit_log_drift':True,
  },
}
Path(sys.argv[1]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_RESULT

{
  echo "checked_at=$(date -Is)"
  echo "task_id=$TASK_ID"
  echo "result=$RESULT"
  echo "plugin_id=$PLUGIN_ID"
  echo "plugin_present_before=$PLUGIN_PRESENT_BEFORE"
  echo "plugin_present_after=$PLUGIN_PRESENT_AFTER"
  echo "uninstall_rc=$UNINSTALL_RC"
  echo "config_restored=$CONFIG_RESTORED"
  echo "service_restart=$SERVICE_RESTART"
  echo "service_state=$SERVICE_STATE"
  echo "direct_root_status=$DIRECT_ROOT_STATUS"
  echo "public_root_status=$PUBLIC_ROOT_STATUS"
  echo "public_root_matches_direct=$PUBLIC_ROOT_MATCHES_DIRECT"
  echo "enqueue_loopback_only=$ENQUEUE_LOOPBACK_ONLY"
  echo "intake_loopback_only=$INTAKE_LOOPBACK_ONLY"
  echo "queue_state_unchanged=$QUEUE_STATE_UNCHANGED"
  echo "oris_worktree_preserved=$ORIS_WORKTREE_PRESERVED"
  echo "product_baseline_preserved=$PRODUCT_BASELINE_PRESERVED"
  echo "marker_archived=$MARKER_ARCHIVED"
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
if [ "$?" -eq 0 ]; then SECRET_SCAN="PASS"; else fail_now "rollback_evidence_secret_scan_failed" "REPAIR_ROLLBACK_EVIDENCE_REDACTION"; fi

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
git -C "$WORKTREE" commit -m "chore(dev-employee): record native plugin rollback $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
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
