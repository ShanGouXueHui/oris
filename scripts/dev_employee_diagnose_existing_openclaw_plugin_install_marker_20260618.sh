#!/usr/bin/env bash

TASK_ID="commercial-openclaw-native-plugin-install-20260618"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
PLUGIN_ID="oris-dev-employee"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_SERVICE="openclaw-gateway.service"
MARKER_FILE="$HOME/.openclaw/private/oris-dev-employee-plugin-install-current.json"
EXPECTED_PRODUCT_COMMIT="bcb93e17ea88704548101f5e4a5c460e15a80ec7"
DOMAIN="control.orisfy.com"
OPENCLAW_PORT="18789"
ENQUEUE_PORT="18891"
INTAKE_PORT="18892"
TOOL_1="oris_queue_status"
TOOL_2="oris_task_status"
TOOL_3="oris_latest_task_status"
HOOK_1="model_call_ended"
HOOK_2="after_tool_call"
HOOK_3="agent_end"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-plugin-marker-diagnostic-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/diagnostic.log"
RESULT_JSON="$TMP_ROOT/diagnostic.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_native_plugin_install"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/openclaw-native-plugin-marker-diagnostic-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/openclaw-native-plugin-marker-diagnostic-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
CLASSIFICATION="UNKNOWN"
MARKER_EXISTS="NO"
MARKER_MODE="unknown"
MARKER_VALID="NO"
MARKER_STATE="unknown"
MARKER_PLUGIN_ID_MATCH="NO"
MARKER_VERSION="unknown"
MARKER_SOURCE_COMMIT=""
MARKER_ARTIFACT_SHA_VALID="NO"
MARKER_DENIED_TOOLS_MATCH="NO"
MARKER_SECRET_KEYS_ABSENT="NO"
BACKUP_FILE=""
BACKUP_EXISTS="NO"
BACKUP_MODE="unknown"
BACKUP_VALID_JSON="NO"
CURRENT_CONFIG_EQUALS_BACKUP="unknown"
AUTH_MODE_MATCHES_BACKUP="unknown"
AUTH_SECRET_MATCHES_BACKUP="unknown"
TOOLS_ALLOW_MATCHES_BACKUP="unknown"
CURRENT_EXPECTED_TOOLS_DENIED="NO"
BACKUP_EXPECTED_TOOLS_DENIED="unknown"
PLUGIN_CONFIG_ENTRY_PRESENT="unknown"
PLUGIN_ALLOW_PRESENT="unknown"
PLUGIN_DENY_PRESENT="unknown"
PLUGIN_PRESENT_COLD="unknown"
PLUGIN_ENABLED_COLD="unknown"
PLUGIN_ERROR_COUNT="unknown"
RUNTIME_INSPECT_RC="not_run"
RUNTIME_TOOL_COUNT="0"
RUNTIME_HOOK_COUNT="0"
RUNTIME_TOOLS_MATCH="NO"
RUNTIME_HOOKS_MATCH="NO"
WRITE_TOOLS_ABSENT="unknown"
SERVICE_STATE="unknown"
DIRECT_ROOT_STATUS="000"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ROOT_MATCHES_DIRECT="NO"
ENQUEUE_LOOPBACK_ONLY="unknown"
INTAKE_LOOPBACK_ONLY="unknown"
ACTIVE_QUEUE_COUNT="unknown"
QUEUE_STATE_UNCHANGED="NO"
ORIS_WORKTREE_PRESERVED="NO"
PRODUCT_BASELINE_PRESERVED="NO"
CONFIG_UNCHANGED="NO"
SERVICE_PID_UNCHANGED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_EXISTING_PLUGIN_INSTALL_STATE"

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
  echo "CLASSIFICATION=$CLASSIFICATION"
  echo "MARKER_EXISTS=$MARKER_EXISTS"
  echo "MARKER_MODE=$MARKER_MODE"
  echo "MARKER_VALID=$MARKER_VALID"
  echo "MARKER_STATE=$MARKER_STATE"
  echo "MARKER_PLUGIN_ID_MATCH=$MARKER_PLUGIN_ID_MATCH"
  echo "MARKER_VERSION=$MARKER_VERSION"
  echo "MARKER_SOURCE_COMMIT=$MARKER_SOURCE_COMMIT"
  echo "MARKER_ARTIFACT_SHA_VALID=$MARKER_ARTIFACT_SHA_VALID"
  echo "MARKER_DENIED_TOOLS_MATCH=$MARKER_DENIED_TOOLS_MATCH"
  echo "MARKER_SECRET_KEYS_ABSENT=$MARKER_SECRET_KEYS_ABSENT"
  echo "BACKUP_FILE=$BACKUP_FILE"
  echo "BACKUP_EXISTS=$BACKUP_EXISTS"
  echo "BACKUP_MODE=$BACKUP_MODE"
  echo "BACKUP_VALID_JSON=$BACKUP_VALID_JSON"
  echo "CURRENT_CONFIG_EQUALS_BACKUP=$CURRENT_CONFIG_EQUALS_BACKUP"
  echo "AUTH_MODE_MATCHES_BACKUP=$AUTH_MODE_MATCHES_BACKUP"
  echo "AUTH_SECRET_MATCHES_BACKUP=$AUTH_SECRET_MATCHES_BACKUP"
  echo "TOOLS_ALLOW_MATCHES_BACKUP=$TOOLS_ALLOW_MATCHES_BACKUP"
  echo "CURRENT_EXPECTED_TOOLS_DENIED=$CURRENT_EXPECTED_TOOLS_DENIED"
  echo "BACKUP_EXPECTED_TOOLS_DENIED=$BACKUP_EXPECTED_TOOLS_DENIED"
  echo "PLUGIN_CONFIG_ENTRY_PRESENT=$PLUGIN_CONFIG_ENTRY_PRESENT"
  echo "PLUGIN_ALLOW_PRESENT=$PLUGIN_ALLOW_PRESENT"
  echo "PLUGIN_DENY_PRESENT=$PLUGIN_DENY_PRESENT"
  echo "PLUGIN_PRESENT_COLD=$PLUGIN_PRESENT_COLD"
  echo "PLUGIN_ENABLED_COLD=$PLUGIN_ENABLED_COLD"
  echo "PLUGIN_ERROR_COUNT=$PLUGIN_ERROR_COUNT"
  echo "RUNTIME_INSPECT_RC=$RUNTIME_INSPECT_RC"
  echo "RUNTIME_TOOL_COUNT=$RUNTIME_TOOL_COUNT"
  echo "RUNTIME_HOOK_COUNT=$RUNTIME_HOOK_COUNT"
  echo "RUNTIME_TOOLS_MATCH=$RUNTIME_TOOLS_MATCH"
  echo "RUNTIME_HOOKS_MATCH=$RUNTIME_HOOKS_MATCH"
  echo "WRITE_TOOLS_ABSENT=$WRITE_TOOLS_ABSENT"
  echo "SERVICE_STATE=$SERVICE_STATE"
  echo "DIRECT_ROOT_STATUS=$DIRECT_ROOT_STATUS"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ROOT_MATCHES_DIRECT=$PUBLIC_ROOT_MATCHES_DIRECT"
  echo "ENQUEUE_LOOPBACK_ONLY=$ENQUEUE_LOOPBACK_ONLY"
  echo "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
  echo "ACTIVE_QUEUE_COUNT=$ACTIVE_QUEUE_COUNT"
  echo "QUEUE_STATE_UNCHANGED=$QUEUE_STATE_UNCHANGED"
  echo "ORIS_WORKTREE_PRESERVED=$ORIS_WORKTREE_PRESERVED"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "CONFIG_UNCHANGED=$CONFIG_UNCHANGED"
  echo "SERVICE_PID_UNCHANGED=$SERVICE_PID_UNCHANGED"
  echo "CONFIG_OR_SERVICE_CHANGED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
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
            stat=path.stat(); rows.append(f"{path.name}\t{stat.st_size}\t{stat.st_mtime_ns}")
        except FileNotFoundError:
            pass
print(hashlib.sha256('\n'.join(rows).encode()).hexdigest())
PY_QUEUE
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
for cmd in git openclaw python3 sha256sum systemctl curl ss stat find awk grep; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$OPENCLAW_CONFIG" ] || fail_now "openclaw_config_missing" "RESTORE_OPENCLAW_CONFIG"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=READ_ONLY_EXISTING_PLUGIN_INSTALL_MARKER_DIAGNOSTIC"
log "CONFIG_OR_SERVICE_CHANGED=NO"
log "PRODUCT_TASK_SUBMITTED=NO"
log "SECRET_VALUES_RECORDED=NO"

ORIS_STATUS_BEFORE_FILE="$TMP_ROOT/oris-status-before.bin"
ORIS_STATUS_AFTER_FILE="$TMP_ROOT/oris-status-after.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_BEFORE_FILE" || fail_now "oris_status_capture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_BEFORE_SHA="$(sha256sum "$ORIS_STATUS_BEFORE_FILE" | awk '{print $1}')"
CONFIG_SHA_BEFORE="$(sha256sum "$OPENCLAW_CONFIG" | awk '{print $1}')"
SERVICE_PID_BEFORE="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"
QUEUE_BEFORE="$(queue_fingerprint)"
PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"

[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_head" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_remote_main" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ -z "$PRODUCT_STATUS_BEFORE" ] || fail_now "product_worktree_not_clean" "RESTORE_COMPLETED_PRODUCT_BASELINE"

ACTIVE_QUEUE_COUNT="$(find "$ORIS_REPO/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' -o -name '*.claimed.json' -o -name '*.planning.json' -o -name '*.executing.json' -o -name '*.committing.json' -o -name '*.pushing.json' -o -name '*.cancelling.json' \) 2>/dev/null | wc -l | tr -d ' ')"

if [ -f "$MARKER_FILE" ]; then
  MARKER_EXISTS="YES"
  MARKER_MODE="$(stat -c '%a' "$MARKER_FILE" 2>/dev/null || echo unknown)"
fi

python3 - "$MARKER_FILE" "$OPENCLAW_CONFIG" "$TMP_ROOT/marker-config-safe.json" "$PLUGIN_ID" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY_MARKER_CONFIG'
import hashlib,json,os,re,sys
from pathlib import Path
marker_path=Path(sys.argv[1]).expanduser()
config_path=Path(sys.argv[2]).expanduser()
out=Path(sys.argv[3])
plugin_id=sys.argv[4]
expected_tools=sys.argv[5:8]
result={
 'marker_exists':marker_path.is_file(),
 'marker_valid':False,
 'marker_state':'unknown',
 'marker_plugin_id_match':False,
 'marker_version':'unknown',
 'marker_source_commit':'',
 'marker_artifact_sha_valid':False,
 'marker_denied_tools_match':False,
 'marker_secret_keys_absent':False,
 'backup_file':'',
 'backup_exists':False,
 'backup_mode':'unknown',
 'backup_valid_json':False,
 'current_config_equals_backup':'unknown',
 'auth_mode_matches_backup':'unknown',
 'auth_secret_matches_backup':'unknown',
 'tools_allow_matches_backup':'unknown',
 'current_expected_tools_denied':False,
 'backup_expected_tools_denied':'unknown',
 'plugin_config_entry_present':False,
 'plugin_allow_present':False,
 'plugin_deny_present':False,
}
allowed_marker_keys={'state','plugin_id','plugin_version','source_commit','artifact_sha256','installed_at','config_backup','denied_tools','secret_values_recorded','runtime_inspected','rollback_script'}
try:
    current=json.loads(config_path.read_text(encoding='utf-8'))
except Exception:
    out.write_text(json.dumps(result,indent=2)+'\n'); raise SystemExit(0)

def config_facts(data):
    gateway=data.get('gateway') if isinstance(data.get('gateway'),dict) else {}
    auth=gateway.get('auth') if isinstance(gateway.get('auth'),dict) else {}
    mode=auth.get('mode') or 'token'
    secret=auth.get(mode) if mode in {'token','password'} else None
    tools=data.get('tools') if isinstance(data.get('tools'),dict) else {}
    allow=tools.get('allow') if isinstance(tools.get('allow'),list) else []
    deny=tools.get('deny') if isinstance(tools.get('deny'),list) else []
    plugins=data.get('plugins') if isinstance(data.get('plugins'),dict) else {}
    entries=plugins.get('entries') if isinstance(plugins.get('entries'),dict) else {}
    p_allow=plugins.get('allow') if isinstance(plugins.get('allow'),list) else []
    p_deny=plugins.get('deny') if isinstance(plugins.get('deny'),list) else []
    return {
      'mode':mode,
      'secret_hash':hashlib.sha256(secret.encode()).hexdigest() if isinstance(secret,str) and secret else None,
      'allow_hash':hashlib.sha256(json.dumps(allow,sort_keys=True).encode()).hexdigest(),
      'deny':deny,
      'plugin_entry_present':plugin_id in entries,
      'plugin_allow_present':plugin_id in p_allow,
      'plugin_deny_present':plugin_id in p_deny,
    }
current_facts=config_facts(current)
result['current_expected_tools_denied']=all(x in current_facts['deny'] for x in expected_tools)
result['plugin_config_entry_present']=current_facts['plugin_entry_present']
result['plugin_allow_present']=current_facts['plugin_allow_present']
result['plugin_deny_present']=current_facts['plugin_deny_present']
if not marker_path.is_file():
    out.write_text(json.dumps(result,indent=2)+'\n'); raise SystemExit(0)
try:
    marker=json.loads(marker_path.read_text(encoding='utf-8'))
except Exception:
    out.write_text(json.dumps(result,indent=2)+'\n'); raise SystemExit(0)
if not isinstance(marker,dict):
    out.write_text(json.dumps(result,indent=2)+'\n'); raise SystemExit(0)
unknown_keys=set(marker)-allowed_marker_keys
result['marker_secret_keys_absent']=not unknown_keys and marker.get('secret_values_recorded') is False
result['marker_state']=str(marker.get('state') or 'unknown')
result['marker_plugin_id_match']=marker.get('plugin_id')==plugin_id
result['marker_version']=str(marker.get('plugin_version') or 'unknown')[:80]
source=str(marker.get('source_commit') or '')
artifact=str(marker.get('artifact_sha256') or '')
result['marker_source_commit']=source if re.fullmatch(r'[0-9a-f]{40}',source) else ''
result['marker_artifact_sha_valid']=bool(re.fullmatch(r'[0-9a-f]{64}',artifact))
denied=marker.get('denied_tools')
result['marker_denied_tools_match']=isinstance(denied,list) and denied==expected_tools
backup_raw=marker.get('config_backup')
backup=None
if isinstance(backup_raw,str) and backup_raw:
    try:
        backup=Path(backup_raw).expanduser().resolve()
        allowed_root=(Path.home()/'.openclaw'/'backups').resolve()
        if backup!=allowed_root and allowed_root not in backup.parents:
            backup=None
    except Exception:
        backup=None
if backup is not None:
    result['backup_file']=str(backup)
    result['backup_exists']=backup.is_file()
    if backup.is_file():
        result['backup_mode']=oct(backup.stat().st_mode & 0o777)[2:]
        try:
            backup_data=json.loads(backup.read_text(encoding='utf-8'))
            result['backup_valid_json']=True
            result['current_config_equals_backup']=hashlib.sha256(config_path.read_bytes()).hexdigest()==hashlib.sha256(backup.read_bytes()).hexdigest()
            backup_facts=config_facts(backup_data)
            result['auth_mode_matches_backup']=current_facts['mode']==backup_facts['mode']
            result['auth_secret_matches_backup']=current_facts['secret_hash'] is not None and current_facts['secret_hash']==backup_facts['secret_hash']
            result['tools_allow_matches_backup']=current_facts['allow_hash']==backup_facts['allow_hash']
            result['backup_expected_tools_denied']=all(x in backup_facts['deny'] for x in expected_tools)
        except Exception:
            pass
result['marker_valid']=(
 result['marker_state'] in {'installing','installed_tools_denied'} and
 result['marker_plugin_id_match'] and
 result['marker_version']!='unknown' and
 bool(result['marker_source_commit']) and
 result['marker_artifact_sha_valid'] and
 result['marker_denied_tools_match'] and
 result['marker_secret_keys_absent'] and
 bool(result['backup_file'])
)
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_MARKER_CONFIG

MARKER_VALID="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["marker_valid"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"
MARKER_STATE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["marker_state"])' "$TMP_ROOT/marker-config-safe.json")"
MARKER_PLUGIN_ID_MATCH="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["marker_plugin_id_match"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"
MARKER_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["marker_version"])' "$TMP_ROOT/marker-config-safe.json")"
MARKER_SOURCE_COMMIT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["marker_source_commit"])' "$TMP_ROOT/marker-config-safe.json")"
MARKER_ARTIFACT_SHA_VALID="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["marker_artifact_sha_valid"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"
MARKER_DENIED_TOOLS_MATCH="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["marker_denied_tools_match"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"
MARKER_SECRET_KEYS_ABSENT="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["marker_secret_keys_absent"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"
BACKUP_FILE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["backup_file"])' "$TMP_ROOT/marker-config-safe.json")"
BACKUP_EXISTS="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["backup_exists"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"
BACKUP_MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["backup_mode"])' "$TMP_ROOT/marker-config-safe.json")"
BACKUP_VALID_JSON="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["backup_valid_json"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"
CURRENT_CONFIG_EQUALS_BACKUP="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["current_config_equals_backup"]; print("YES" if v is True else "NO" if v is False else "unknown")' "$TMP_ROOT/marker-config-safe.json")"
AUTH_MODE_MATCHES_BACKUP="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["auth_mode_matches_backup"]; print("YES" if v is True else "NO" if v is False else "unknown")' "$TMP_ROOT/marker-config-safe.json")"
AUTH_SECRET_MATCHES_BACKUP="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["auth_secret_matches_backup"]; print("YES" if v is True else "NO" if v is False else "unknown")' "$TMP_ROOT/marker-config-safe.json")"
TOOLS_ALLOW_MATCHES_BACKUP="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["tools_allow_matches_backup"]; print("YES" if v is True else "NO" if v is False else "unknown")' "$TMP_ROOT/marker-config-safe.json")"
CURRENT_EXPECTED_TOOLS_DENIED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["current_expected_tools_denied"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"
BACKUP_EXPECTED_TOOLS_DENIED="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["backup_expected_tools_denied"]; print("YES" if v is True else "NO" if v is False else "unknown")' "$TMP_ROOT/marker-config-safe.json")"
PLUGIN_CONFIG_ENTRY_PRESENT="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["plugin_config_entry_present"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"
PLUGIN_ALLOW_PRESENT="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["plugin_allow_present"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"
PLUGIN_DENY_PRESENT="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["plugin_deny_present"] else "NO")' "$TMP_ROOT/marker-config-safe.json")"

openclaw plugins list --json > "$TMP_ROOT/plugins-list.json" 2> "$TMP_ROOT/plugins-list.err"
PLUGIN_LIST_RC="$?"
[ "$PLUGIN_LIST_RC" = "0" ] || fail_now "plugin_list_failed" "INSPECT_OPENCLAW_PLUGIN_REGISTRY"
openclaw plugins inspect "$PLUGIN_ID" --runtime --json > "$TMP_ROOT/plugin-runtime.json" 2> "$TMP_ROOT/plugin-runtime.err"
RUNTIME_INSPECT_RC="$?"

python3 - "$TMP_ROOT/plugins-list.json" "$TMP_ROOT/plugin-runtime.json" "$TMP_ROOT/plugin-runtime-safe.json" "$PLUGIN_ID" "$TOOL_1" "$TOOL_2" "$TOOL_3" "$HOOK_1" "$HOOK_2" "$HOOK_3" "$RUNTIME_INSPECT_RC" <<'PY_RUNTIME'
import json,sys
from pathlib import Path
listing=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
plugin_id=sys.argv[4]; expected_tools=set(sys.argv[5:8]); expected_hooks=set(sys.argv[8:11]); runtime_rc=int(sys.argv[11])
plugins=listing.get('plugins') if isinstance(listing,dict) else []
present=False; enabled=False; errors=0
if isinstance(plugins,list):
    for item in plugins:
        if not isinstance(item,dict): continue
        pid=str(item.get('id') or item.get('name') or '')
        if pid!=plugin_id: continue
        present=True; enabled=item.get('enabled') is True
        if item.get('status')=='error' or item.get('error'): errors+=1
tools=set(); hooks=set()
def add(value,target):
    if isinstance(value,list):
        for x in value:
            if isinstance(x,str): target.add(x)
            elif isinstance(x,dict):
                name=x.get('name') or x.get('id') or x.get('toolName') or x.get('hookName')
                if isinstance(name,str): target.add(name)
    elif isinstance(value,dict):
        for key in value:
            if isinstance(key,str): target.add(key)
def walk(value):
    if isinstance(value,dict):
        for key,child in value.items():
            low=str(key).lower()
            if low in {'tools','registeredtools','toolnames'}: add(child,tools)
            elif low in {'hooks','registeredhooks','hooknames'}: add(child,hooks)
            walk(child)
    elif isinstance(value,list):
        for child in value: walk(child)
if runtime_rc==0:
    try: walk(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
    except Exception: pass
write_tools={'oris_submit_task','oris_cancel_task','oris_retry_task'}
payload={
 'plugin_present_cold':present,
 'plugin_enabled_cold':enabled,
 'plugin_error_count':errors,
 'runtime_tool_count':len(tools),
 'runtime_hook_count':len(hooks),
 'runtime_tools_match':tools==expected_tools,
 'runtime_hooks_match':expected_hooks.issubset(hooks),
 'write_tools_absent':not bool(tools & write_tools),
 'secret_values_recorded':False,
}
Path(sys.argv[3]).write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
PY_RUNTIME
PLUGIN_PRESENT_COLD="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["plugin_present_cold"] else "NO")' "$TMP_ROOT/plugin-runtime-safe.json")"
PLUGIN_ENABLED_COLD="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["plugin_enabled_cold"] else "NO")' "$TMP_ROOT/plugin-runtime-safe.json")"
PLUGIN_ERROR_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["plugin_error_count"])' "$TMP_ROOT/plugin-runtime-safe.json")"
RUNTIME_TOOL_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["runtime_tool_count"])' "$TMP_ROOT/plugin-runtime-safe.json")"
RUNTIME_HOOK_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["runtime_hook_count"])' "$TMP_ROOT/plugin-runtime-safe.json")"
RUNTIME_TOOLS_MATCH="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["runtime_tools_match"] else "NO")' "$TMP_ROOT/plugin-runtime-safe.json")"
RUNTIME_HOOKS_MATCH="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["runtime_hooks_match"] else "NO")' "$TMP_ROOT/plugin-runtime-safe.json")"
WRITE_TOOLS_ABSENT="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["write_tools_absent"] else "NO")' "$TMP_ROOT/plugin-runtime-safe.json")"

SERVICE_STATE="$(systemctl --user is-active "$OPENCLAW_SERVICE" 2>/dev/null || true)"
DIRECT_ROOT_STATUS="$(curl -sS --max-time 8 -o "$TMP_ROOT/direct.body" -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 8 -H 'Cache-Control: no-cache' -o "$TMP_ROOT/public.body" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
DIRECT_SHA="$(sha256sum "$TMP_ROOT/direct.body" 2>/dev/null | awk '{print $1}')"
PUBLIC_SHA="$(sha256sum "$TMP_ROOT/public.body" 2>/dev/null | awk '{print $1}')"
if [ "$DIRECT_ROOT_STATUS" = "200" ] && [ "$PUBLIC_ROOT_STATUS" = "200" ] && [ -n "$DIRECT_SHA" ] && [ "$DIRECT_SHA" = "$PUBLIC_SHA" ]; then PUBLIC_ROOT_MATCHES_DIRECT="YES"; fi
ENQUEUE_LOOPBACK_ONLY="$(loopback_only "$ENQUEUE_PORT")"
INTAKE_LOOPBACK_ONLY="$(loopback_only "$INTAKE_PORT")"

if [ "$MARKER_EXISTS" != "YES" ]; then
  CLASSIFICATION="MARKER_MISSING"
  FAILURE_CODE="marker_disappeared_before_diagnostic"
  NEXT_ACTION="RERUN_CONTROLLED_PLUGIN_INSTALL"
elif [ "$MARKER_VALID" != "YES" ] || [ "$MARKER_MODE" != "600" ]; then
  CLASSIFICATION="INVALID_OR_UNTRUSTED_MARKER"
  FAILURE_CODE="existing_plugin_install_marker_invalid"
  NEXT_ACTION="BUILD_CONTROLLED_MARKER_QUARANTINE_AFTER_REVIEW"
elif [ "$BACKUP_EXISTS" != "YES" ] || [ "$BACKUP_MODE" != "600" ] || [ "$BACKUP_VALID_JSON" != "YES" ]; then
  CLASSIFICATION="INTERRUPTED_INSTALL_BACKUP_UNAVAILABLE"
  FAILURE_CODE="existing_plugin_install_backup_unavailable"
  NEXT_ACTION="DO_NOT_DELETE_MARKER_OR_RESTART;RECONSTRUCT_SAFE_ROLLBACK_PLAN"
elif [ "$MARKER_STATE" = "installed_tools_denied" ] && [ "$PLUGIN_PRESENT_COLD" = "YES" ] && [ "$PLUGIN_ENABLED_COLD" = "YES" ] && [ "$PLUGIN_ERROR_COUNT" = "0" ] && [ "$RUNTIME_TOOLS_MATCH" = "YES" ] && [ "$RUNTIME_HOOKS_MATCH" = "YES" ] && [ "$WRITE_TOOLS_ABSENT" = "YES" ] && [ "$CURRENT_EXPECTED_TOOLS_DENIED" = "YES" ] && [ "$SERVICE_STATE" = "active" ] && [ "$PUBLIC_ROOT_MATCHES_DIRECT" = "YES" ]; then
  CLASSIFICATION="ALREADY_INSTALLED_TOOLS_DENIED"
  RESULT="DIAGNOSED"
  NEXT_ACTION="SKIP_REINSTALL_AND_DESIGN_CONTROLLED_READ_ONLY_TOOL_ENABLE"
elif [ "$MARKER_STATE" = "installing" ] && [ "$PLUGIN_PRESENT_COLD" = "NO" ] && [ "$CURRENT_CONFIG_EQUALS_BACKUP" = "YES" ] && [ "$CURRENT_EXPECTED_TOOLS_DENIED" = "$BACKUP_EXPECTED_TOOLS_DENIED" ]; then
  CLASSIFICATION="STALE_PREMUTATION_MARKER"
  RESULT="DIAGNOSED"
  NEXT_ACTION="ARCHIVE_STALE_MARKER_THEN_RERUN_INSTALL"
elif [ "$MARKER_STATE" = "installing" ]; then
  CLASSIFICATION="INTERRUPTED_AFTER_MUTATION"
  RESULT="DIAGNOSED"
  NEXT_ACTION="RUN_EXISTING_REVERSIBLE_PLUGIN_ROLLBACK"
else
  CLASSIFICATION="INCONSISTENT_COMPLETED_INSTALL"
  FAILURE_CODE="plugin_marker_runtime_state_inconsistent"
  NEXT_ACTION="RUN_EXISTING_REVERSIBLE_PLUGIN_ROLLBACK"
fi

CONFIG_SHA_AFTER="$(sha256sum "$OPENCLAW_CONFIG" | awk '{print $1}')"
SERVICE_PID_AFTER="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"
QUEUE_AFTER="$(queue_fingerprint)"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_AFTER_FILE" || fail_now "oris_status_recapture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_AFTER_SHA="$(sha256sum "$ORIS_STATUS_AFTER_FILE" | awk '{print $1}')"
PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"

[ "$CONFIG_SHA_BEFORE" = "$CONFIG_SHA_AFTER" ] && CONFIG_UNCHANGED="YES"
[ "$SERVICE_PID_BEFORE" = "$SERVICE_PID_AFTER" ] && SERVICE_PID_UNCHANGED="YES"
[ "$QUEUE_BEFORE" = "$QUEUE_AFTER" ] && QUEUE_STATE_UNCHANGED="YES"
[ "$ORIS_STATUS_BEFORE_SHA" = "$ORIS_STATUS_AFTER_SHA" ] && ORIS_WORKTREE_PRESERVED="YES"
if [ "$PRODUCT_HEAD_BEFORE" = "$PRODUCT_HEAD_AFTER" ] && [ "$PRODUCT_REMOTE_BEFORE" = "$PRODUCT_REMOTE_AFTER" ] && [ "$PRODUCT_STATUS_BEFORE" = "$PRODUCT_STATUS_AFTER" ] && [ "$PRODUCT_TREE_BEFORE" = "$PRODUCT_TREE_AFTER" ]; then PRODUCT_BASELINE_PRESERVED="YES"; fi

[ "$CONFIG_UNCHANGED" = "YES" ] || fail_now "config_changed_during_read_only_diagnostic" "INSPECT_UNEXPECTED_CONFIG_MUTATION"
[ "$SERVICE_PID_UNCHANGED" = "YES" ] || fail_now "service_restarted_during_read_only_diagnostic" "INSPECT_UNEXPECTED_SERVICE_CHANGE"
[ "$QUEUE_STATE_UNCHANGED" = "YES" ] || fail_now "queue_changed_during_read_only_diagnostic" "INSPECT_UNEXPECTED_QUEUE_MUTATION"
[ "$ORIS_WORKTREE_PRESERVED" = "YES" ] || fail_now "oris_worktree_changed_during_read_only_diagnostic" "INSPECT_UNEXPECTED_ORIS_MUTATION"
[ "$PRODUCT_BASELINE_PRESERVED" = "YES" ] || fail_now "product_baseline_changed_during_read_only_diagnostic" "RESTORE_COMPLETED_PRODUCT_BASELINE"

export TASK_ID STAMP RESULT FAILURE_CODE CLASSIFICATION MARKER_EXISTS MARKER_MODE MARKER_VALID MARKER_STATE MARKER_PLUGIN_ID_MATCH MARKER_VERSION MARKER_SOURCE_COMMIT MARKER_ARTIFACT_SHA_VALID MARKER_DENIED_TOOLS_MATCH MARKER_SECRET_KEYS_ABSENT BACKUP_FILE BACKUP_EXISTS BACKUP_MODE BACKUP_VALID_JSON CURRENT_CONFIG_EQUALS_BACKUP AUTH_MODE_MATCHES_BACKUP AUTH_SECRET_MATCHES_BACKUP TOOLS_ALLOW_MATCHES_BACKUP CURRENT_EXPECTED_TOOLS_DENIED BACKUP_EXPECTED_TOOLS_DENIED PLUGIN_CONFIG_ENTRY_PRESENT PLUGIN_ALLOW_PRESENT PLUGIN_DENY_PRESENT PLUGIN_PRESENT_COLD PLUGIN_ENABLED_COLD PLUGIN_ERROR_COUNT RUNTIME_INSPECT_RC RUNTIME_TOOL_COUNT RUNTIME_HOOK_COUNT RUNTIME_TOOLS_MATCH RUNTIME_HOOKS_MATCH WRITE_TOOLS_ABSENT SERVICE_STATE DIRECT_ROOT_STATUS PUBLIC_ROOT_STATUS PUBLIC_ROOT_MATCHES_DIRECT ENQUEUE_LOOPBACK_ONLY INTAKE_LOOPBACK_ONLY ACTIVE_QUEUE_COUNT QUEUE_STATE_UNCHANGED ORIS_WORKTREE_PRESERVED PRODUCT_BASELINE_PRESERVED CONFIG_UNCHANGED SERVICE_PID_UNCHANGED NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path

def yes(name): return os.environ.get(name)=='YES'
payload={
 'task_id':os.environ['TASK_ID'],
 'checked_at':os.environ['STAMP'],
 'result':os.environ['RESULT'],
 'failure_code':os.environ.get('FAILURE_CODE') or None,
 'classification':os.environ['CLASSIFICATION'],
 'marker':{
   'exists':yes('MARKER_EXISTS'),'mode':os.environ['MARKER_MODE'],'valid':yes('MARKER_VALID'),
   'state':os.environ['MARKER_STATE'],'plugin_id_match':yes('MARKER_PLUGIN_ID_MATCH'),
   'version':os.environ['MARKER_VERSION'],'source_commit':os.environ['MARKER_SOURCE_COMMIT'],
   'artifact_sha_valid':yes('MARKER_ARTIFACT_SHA_VALID'),
   'denied_tools_match':yes('MARKER_DENIED_TOOLS_MATCH'),
   'secret_keys_absent':yes('MARKER_SECRET_KEYS_ABSENT'),
 },
 'backup':{
   'file':os.environ['BACKUP_FILE'],'exists':yes('BACKUP_EXISTS'),'mode':os.environ['BACKUP_MODE'],
   'valid_json':yes('BACKUP_VALID_JSON'),'current_config_equals_backup':os.environ['CURRENT_CONFIG_EQUALS_BACKUP'],
   'auth_mode_matches':os.environ['AUTH_MODE_MATCHES_BACKUP'],'auth_secret_matches':os.environ['AUTH_SECRET_MATCHES_BACKUP'],
   'tools_allow_matches':os.environ['TOOLS_ALLOW_MATCHES_BACKUP'],
   'backup_expected_tools_denied':os.environ['BACKUP_EXPECTED_TOOLS_DENIED'],
 },
 'current_config':{
   'expected_tools_denied':yes('CURRENT_EXPECTED_TOOLS_DENIED'),
   'plugin_entry_present':yes('PLUGIN_CONFIG_ENTRY_PRESENT'),
   'plugin_allow_present':yes('PLUGIN_ALLOW_PRESENT'),
   'plugin_deny_present':yes('PLUGIN_DENY_PRESENT'),
 },
 'plugin_runtime':{
   'present_cold':yes('PLUGIN_PRESENT_COLD'),'enabled_cold':yes('PLUGIN_ENABLED_COLD'),
   'error_count':os.environ['PLUGIN_ERROR_COUNT'],'runtime_inspect_rc':os.environ['RUNTIME_INSPECT_RC'],
   'tool_count':int(os.environ['RUNTIME_TOOL_COUNT']),'hook_count':int(os.environ['RUNTIME_HOOK_COUNT']),
   'tools_match':yes('RUNTIME_TOOLS_MATCH'),'hooks_match':yes('RUNTIME_HOOKS_MATCH'),
   'write_tools_absent':yes('WRITE_TOOLS_ABSENT'),
 },
 'gateway':{
   'state':os.environ['SERVICE_STATE'],'direct_root_status':os.environ['DIRECT_ROOT_STATUS'],
   'public_root_status':os.environ['PUBLIC_ROOT_STATUS'],'public_matches_direct':yes('PUBLIC_ROOT_MATCHES_DIRECT'),
 },
 'safety':{
   'enqueue_loopback_only':yes('ENQUEUE_LOOPBACK_ONLY'),'intake_loopback_only':yes('INTAKE_LOOPBACK_ONLY'),
   'active_queue_count':os.environ['ACTIVE_QUEUE_COUNT'],'queue_state_unchanged':yes('QUEUE_STATE_UNCHANGED'),
   'oris_worktree_preserved':yes('ORIS_WORKTREE_PRESERVED'),'product_baseline_preserved':yes('PRODUCT_BASELINE_PRESERVED'),
   'config_unchanged':yes('CONFIG_UNCHANGED'),'service_pid_unchanged':yes('SERVICE_PID_UNCHANGED'),
   'product_task_submitted':False,'secret_values_recorded':False,
 },
 'next_action':os.environ['NEXT_ACTION'],
 'evidence':{'log_path':os.environ['EVIDENCE_LOG_REL'],'json_path':os.environ['EVIDENCE_JSON_REL'],'self_commit_sha_omitted_to_prevent_post_commit_log_drift':True},
}
Path(sys.argv[1]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_RESULT

{
  echo "checked_at=$(date -Is)"
  echo "task_id=$TASK_ID"
  echo "result=$RESULT"
  echo "failure_code=$FAILURE_CODE"
  echo "classification=$CLASSIFICATION"
  echo "marker_exists=$MARKER_EXISTS"
  echo "marker_mode=$MARKER_MODE"
  echo "marker_valid=$MARKER_VALID"
  echo "marker_state=$MARKER_STATE"
  echo "backup_exists=$BACKUP_EXISTS"
  echo "backup_mode=$BACKUP_MODE"
  echo "current_config_equals_backup=$CURRENT_CONFIG_EQUALS_BACKUP"
  echo "current_expected_tools_denied=$CURRENT_EXPECTED_TOOLS_DENIED"
  echo "plugin_present_cold=$PLUGIN_PRESENT_COLD"
  echo "plugin_enabled_cold=$PLUGIN_ENABLED_COLD"
  echo "plugin_error_count=$PLUGIN_ERROR_COUNT"
  echo "runtime_tools_match=$RUNTIME_TOOLS_MATCH"
  echo "runtime_hooks_match=$RUNTIME_HOOKS_MATCH"
  echo "write_tools_absent=$WRITE_TOOLS_ABSENT"
  echo "service_state=$SERVICE_STATE"
  echo "direct_root_status=$DIRECT_ROOT_STATUS"
  echo "public_root_status=$PUBLIC_ROOT_STATUS"
  echo "public_matches_direct=$PUBLIC_ROOT_MATCHES_DIRECT"
  echo "queue_state_unchanged=$QUEUE_STATE_UNCHANGED"
  echo "config_unchanged=$CONFIG_UNCHANGED"
  echo "service_pid_unchanged=$SERVICE_PID_UNCHANGED"
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
if [ "$?" -eq 0 ]; then SECRET_SCAN="PASS"; else fail_now "diagnostic_evidence_secret_scan_failed" "REPAIR_DIAGNOSTIC_EVIDENCE_REDACTION"; fi

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
git -C "$WORKTREE" commit -m "chore(dev-employee): diagnose existing native plugin install marker $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
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
