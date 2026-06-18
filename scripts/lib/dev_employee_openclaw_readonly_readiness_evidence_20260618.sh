# Build sanitized evidence. Raw OpenClaw/config/marker/plugin outputs remain only in the private temp directory.
export TASK_ID STAMP RESULT FAILURE_CODE NEXT_ACTION CHECK_TOTAL CHECK_PASS CHECK_REVIEW CHECK_FAIL
export ACTIVE_QUEUE_COUNT_BEFORE ACTIVE_QUEUE_COUNT_AFTER DIRECT_ROOT_STATUS PUBLIC_ROOT_STATUS ADMIN_STATUS ROLLBACK_SHELL_STATUS
export ENQUEUE_LOOPBACK_ONLY INTAKE_LOOPBACK_ONLY WEB_CONSOLE_LOOPBACK_ONLY OPENCLAW_VERSION AUTH_MODE
export EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$RESULT_JSON" "$TMP_ROOT/marker-safe.json" "$TMP_ROOT/config-safe.json" "$TMP_ROOT/runtime-safe.json" "$TMP_ROOT/telemetry-safe.json" "$RUN_LOG" <<'PY_RESULT'
import json, os, sys
from pathlib import Path
result_path, marker_path, config_path, runtime_path, telemetry_path, log_path = map(Path, sys.argv[1:])
checks=[]
for line in log_path.read_text(encoding='utf-8',errors='replace').splitlines():
 if not line.startswith('CHECK|'): continue
 _,name,status,detail=line.split('|',3)
 checks.append({'name':name,'status':status,'detail':detail})

def read_json(path):
 try: return json.loads(path.read_text(encoding='utf-8'))
 except Exception: return {'parse_ok':False}
payload={
 'task_id':os.environ['TASK_ID'],
 'checked_at':os.environ['STAMP'],
 'result':os.environ['RESULT'],
 'failure_code':os.environ.get('FAILURE_CODE') or None,
 'mode':'read_only_readiness_no_config_mutation',
 'checks':checks,
 'check_summary':{
  'total':int(os.environ['CHECK_TOTAL']),
  'pass':int(os.environ['CHECK_PASS']),
  'review':int(os.environ['CHECK_REVIEW']),
  'fail':int(os.environ['CHECK_FAIL']),
 },
 'marker_and_backup':read_json(marker_path),
 'policy':read_json(config_path),
 'plugin_runtime':read_json(runtime_path),
 'telemetry':read_json(telemetry_path),
 'network':{
  'direct_root_status':os.environ['DIRECT_ROOT_STATUS'],
  'public_root_status':os.environ['PUBLIC_ROOT_STATUS'],
  'admin_unauthenticated_status':os.environ['ADMIN_STATUS'],
  'rollback_shell_unauthenticated_status':os.environ['ROLLBACK_SHELL_STATUS'],
  'enqueue_loopback_only':os.environ['ENQUEUE_LOOPBACK_ONLY']=='YES',
  'intake_loopback_only':os.environ['INTAKE_LOOPBACK_ONLY']=='YES',
  'web_console_loopback_only':os.environ['WEB_CONSOLE_LOOPBACK_ONLY']=='YES',
 },
 'queue':{
  'active_count_before':int(os.environ['ACTIVE_QUEUE_COUNT_BEFORE']),
  'active_count_after':int(os.environ['ACTIVE_QUEUE_COUNT_AFTER']),
  'fingerprint_value_omitted':True,
 },
 'runtime_versions':{'openclaw':os.environ['OPENCLAW_VERSION']},
 'safety':{
  'config_mutated':False,
  'gateway_restarted_or_reloaded':False,
  'tools_enabled':False,
  'write_tools_added':False,
  'product_task_submitted':False,
  'marker_or_config_raw_content_recorded':False,
  'secret_values_recorded':False,
 },
 'next_action':os.environ['NEXT_ACTION'],
 'evidence':{
  'log_path':os.environ['EVIDENCE_LOG_REL'],
  'json_path':os.environ['EVIDENCE_JSON_REL'],
  'self_commit_sha_omitted_to_prevent_post_commit_log_drift':True,
 },
}
# Credential values are never copied into the structural policy summary.
result_path.write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
PY_RESULT
[ "$?" -eq 0 ] || fatal "sanitized_evidence_build_failed" "INSPECT_READINESS_SCRIPT"

# Final log contains only bounded, sanitized status fields.
log "result=$RESULT"
log "failure_code=$FAILURE_CODE"
log "checks_total=$CHECK_TOTAL"
log "checks_pass=$CHECK_PASS"
log "checks_review=$CHECK_REVIEW"
log "checks_fail=$CHECK_FAIL"
log "active_queue_count_before=$ACTIVE_QUEUE_COUNT_BEFORE"
log "active_queue_count_after=$ACTIVE_QUEUE_COUNT_AFTER"
log "config_mutated=NO"
log "gateway_restarted_or_reloaded=NO"
log "tools_enabled=NO"
log "product_task_submitted=NO"
log "secret_values_recorded=NO"

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY_SCAN'
import re,sys
from pathlib import Path
patterns=[
 re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
 re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),
 re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),
 re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
 re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
 re.compile(r'Bearer\s+[A-Za-z0-9._~+/=-]{12,}',re.I),
 re.compile(r'"(?:token|password|secret|credential|authorization|cookie|prompt|messages?|content|toolArguments?|toolResults?)"\s*:',re.I),
]
for filename in sys.argv[1:]:
 text=Path(filename).read_text(encoding='utf-8',errors='replace')
 if any(pattern.search(text) for pattern in patterns): raise SystemExit(1)
PY_SCAN
[ "$?" -eq 0 ] || fatal "readiness_evidence_secret_or_content_scan_failed" "INSPECT_PRIVATE_TEMP_EVIDENCE_ONLY"

# Commit evidence through a detached worktree so the primary worktree remains untouched.
git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fatal "evidence_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fatal "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL" || fatal "evidence_directory_create_failed" "CHECK_EVIDENCE_WORKTREE_PERMISSIONS"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_COPY'
import json,sys
from pathlib import Path
sl,dl,sj,dj=map(Path,sys.argv[1:])
dl.write_text('\n'.join(line.rstrip(' \t\r') for line in sl.read_text(encoding='utf-8',errors='replace').splitlines())+'\n',encoding='utf-8')
dj.write_text(json.dumps(json.loads(sj.read_text(encoding='utf-8')),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
PY_COPY
[ "$?" -eq 0 ] || fatal "evidence_copy_failed" "INSPECT_EVIDENCE_WORKTREE"
python3 - "$WORKTREE/$EVIDENCE_LOG_REL" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_FINAL_SCAN'
import re,sys
from pathlib import Path
patterns=[
 re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
 re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),
 re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),
 re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
 re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
 re.compile(r'Bearer\s+[A-Za-z0-9._~+/=-]{12,}',re.I),
 re.compile(r'"(?:token|password|secret|credential|authorization|cookie|prompt|messages?|content|toolArguments?|toolResults?)"\s*:',re.I),
]
for filename in sys.argv[1:]:
 text=Path(filename).read_text(encoding='utf-8',errors='replace')
 if any(pattern.search(text) for pattern in patterns): raise SystemExit(1)
PY_FINAL_SCAN
[ "$?" -eq 0 ] || fatal "final_committed_evidence_secret_or_content_scan_failed" "INSPECT_PRIVATE_TEMP_EVIDENCE_ONLY"
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fatal "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fatal "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record read-only tool readiness $STAMP" >/dev/null 2>&1 || fatal "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fatal "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fatal "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fatal "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ -n "$EVIDENCE_COMMIT" ] && [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ]; then
  EVIDENCE_REMOTE_VERIFIED="YES"
else
  fatal "evidence_remote_sha_mismatch" "VERIFY_ORIS_REMOTE_MAIN"
fi

summary
[ "$RESULT" = "READY" ] && exit 0
[ "$RESULT" = "REVIEW" ] && exit 2
exit 1
