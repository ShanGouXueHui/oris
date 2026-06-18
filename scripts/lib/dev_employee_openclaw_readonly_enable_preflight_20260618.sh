for cmd in git openclaw python3 sha256sum systemctl curl ss stat find wc awk grep sed tr seq cp chmod mkdir date; do
  command -v "$cmd" >/dev/null 2>&1 || fatal "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ "$(id -un 2>/dev/null)" = "admin" ] || fatal "wrong_linux_user" "RUN_AS_ADMIN"
[ -d "$ORIS_REPO/.git" ] || fatal "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fatal "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$OPENCLAW_CONFIG" ] || fatal "openclaw_config_missing" "RESTORE_OPENCLAW_CONFIG"
[ -f "$MARKER_FILE" ] || fatal "install_marker_missing" "RESTORE_PRIVATE_INSTALL_MARKER"

log "checked_at=$(date -Is)"
log "task_id=$TASK_ID"
log "mode=REVERSIBLE_READ_ONLY_ENABLEMENT_WITH_BROWSER_ACCEPTANCE"
log "product_task_submitted=NO"
log "write_tools_added=NO"
log "openclaw_reinstalled_or_upgraded=NO"
log "secret_values_recorded=NO"

git -C "$ORIS_REPO" fetch origin main >/dev/null 2>&1 || fatal "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" merge-base --is-ancestor "$READINESS_COMMIT" origin/main >/dev/null 2>&1 || fatal "readiness_commit_not_on_main" "RESTORE_AUTHORITATIVE_READINESS_EVIDENCE"
READINESS_RESULT="$(git -C "$ORIS_REPO" show "$READINESS_COMMIT:$READINESS_JSON_REL" 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("result", ""))' 2>/dev/null || true)"
[ "$READINESS_RESULT" = "READY" ] || fatal "readiness_evidence_not_ready" "RERUN_READ_ONLY_READINESS"
record_check "authoritative_readiness" "PASS" "ready_evidence_commit_verified"

python3 - "$OPENCLAW_CONFIG" "$MARKER_FILE" "$TMP_ROOT/preflight-safe.json" "$PLUGIN_ID" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY'
import json,os,sys
from pathlib import Path
config=Path(sys.argv[1]); marker=Path(sys.argv[2]); out=Path(sys.argv[3]); plugin=sys.argv[4]; expected=set(sys.argv[5:8])
data=json.loads(config.read_text(encoding='utf-8')); mark=json.loads(marker.read_text(encoding='utf-8'))
tools=data.get('tools') if isinstance(data.get('tools'),dict) else {}
allow=tools.get('allow',None); deny=tools.get('deny',None)
plugins=data.get('plugins') if isinstance(data.get('plugins'),dict) else {}
entries=plugins.get('entries') if isinstance(plugins.get('entries'),dict) else {}
entry=entries.get(plugin) if isinstance(entries.get(plugin),dict) else {}
hooks=entry.get('hooks') if isinstance(entry.get('hooks'),dict) else {}
auth=data.get('gateway',{}).get('auth',{}) if isinstance(data.get('gateway'),dict) else {}
agent_defaults=data.get('agents',{}).get('defaults',{}) if isinstance(data.get('agents'),dict) else {}
agent_tools=agent_defaults.get('tools') if isinstance(agent_defaults,dict) and isinstance(agent_defaults.get('tools'),dict) else {}
payload={
 'config_owner_ok':config.stat().st_uid==os.getuid(),'config_mode_ok':(config.stat().st_mode & 0o777)==0o600,
 'marker_owner_ok':marker.stat().st_uid==os.getuid(),'marker_mode_ok':(marker.stat().st_mode & 0o777)==0o600,
 'marker_state_ok':mark.get('state')=='installed_tools_denied','marker_plugin_ok':mark.get('plugin_id')==plugin,
 'profile_ok':tools.get('profile')=='coding','allow_absent':allow is None,
 'deny_exact':isinstance(deny,list) and set(deny)==expected and len(deny)==3,
 'agent_allow_absent':agent_tools.get('allow') is None,'agent_deny_absent':agent_tools.get('deny') is None,
 'conversation_access_ok':hooks.get('allowConversationAccess') is True,'plugin_enabled':entry.get('enabled') is True,
 'auth_mode_ok':auth.get('mode')=='token','auth_token_private_string':isinstance(auth.get('token'),str) and bool(auth.get('token')),
 'secret_values_recorded':False,
}
out.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n',encoding='utf-8')
PY
[ "$?" -eq 0 ] || fatal "preflight_safe_parse_failed" "INSPECT_OPENCLAW_CONFIG_PRIVATELY"
PREFLIGHT_OK="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("YES" if all(v is True for k,v in d.items() if k!="secret_values_recorded") else "NO")' "$TMP_ROOT/preflight-safe.json")"
[ "$PREFLIGHT_OK" = "YES" ] || fatal "preflight_policy_or_marker_mismatch" "RERUN_READINESS_WITHOUT_ENABLING_TOOLS"
record_check "current_tools_denied_policy" "PASS" "coding_profile_exact_three_deny_no_allow"

GATEWAY_PID_BEFORE="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"
GATEWAY_STATE_BEFORE="$(systemctl --user is-active "$OPENCLAW_SERVICE" 2>/dev/null || true)"
DIRECT_ROOT_BEFORE="$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
[ "$GATEWAY_STATE_BEFORE" = "active" ] && [ "$DIRECT_ROOT_BEFORE" = "200" ] || fatal "gateway_not_healthy_before_enablement" "RESTORE_GATEWAY_HEALTH"
record_check "gateway_pre_enablement_health" "PASS" "active_root_200"

[ "$(loopback_only "$ENQUEUE_PORT")" = "YES" ] || fatal "enqueue_not_loopback_only" "RESTORE_PRIVATE_LISTENER"
[ "$(loopback_only "$INTAKE_PORT")" = "YES" ] || fatal "intake_not_loopback_only" "RESTORE_PRIVATE_LISTENER"
record_check "private_status_and_intake_listeners" "PASS" "18891_and_18892_loopback_only"

QUEUE_FINGERPRINT_BEFORE="$(queue_fingerprint)"
ACTIVE_QUEUE_BEFORE="$(active_queue_count)"
[ "$ACTIVE_QUEUE_BEFORE" = "0" ] || fatal "active_queue_present" "WAIT_FOR_QUEUE_TO_DRAIN"
PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE_FILE="$TMP_ROOT/product-status-before.bin"
git -C "$PRODUCT_REPO" status --porcelain=v1 -z --untracked-files=all > "$PRODUCT_STATUS_BEFORE_FILE" || fatal "product_status_capture_failed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_STATUS_SHA_BEFORE="$(sha256sum "$PRODUCT_STATUS_BEFORE_FILE" | awk '{print $1}')"
PRODUCT_TREE_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
EMPTY_SHA="$(printf '' | sha256sum | awk '{print $1}')"
[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] && [ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] && [ "$PRODUCT_STATUS_SHA_BEFORE" = "$EMPTY_SHA" ] || fatal "product_baseline_mismatch" "RESTORE_COMPLETED_PRODUCT_BASELINE"
record_check "product_baseline" "PASS" "head_remote_main_exact_and_clean"

ORIS_HEAD_BEFORE="$(git -C "$ORIS_REPO" rev-parse HEAD 2>/dev/null || true)"
ORIS_STATUS_BEFORE_FILE="$TMP_ROOT/oris-status-before.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_BEFORE_FILE" || fatal "oris_status_capture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_SHA_BEFORE="$(sha256sum "$ORIS_STATUS_BEFORE_FILE" | awk '{print $1}')"

mkdir -p "$BACKUP_DIR" || fatal "enablement_backup_directory_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
chmod 700 "$BACKUP_DIR" || fatal "enablement_backup_directory_permission_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
cp "$OPENCLAW_CONFIG" "$CONFIG_BACKUP_FILE" || fatal "tools_denied_config_backup_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
cp "$MARKER_FILE" "$MARKER_BACKUP_FILE" || fatal "tools_denied_marker_backup_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
chmod 600 "$CONFIG_BACKUP_FILE" "$MARKER_BACKUP_FILE" || fatal "enablement_backup_permission_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
CONFIG_BACKUP_SHA="$(sha256sum "$CONFIG_BACKUP_FILE" | awk '{print $1}')"
record_check "enablement_backup" "PASS" "private_config_and_marker_backup_created"

python3 - "$OPENCLAW_CONFIG" "$TMP_ROOT/baseline-tool-safe.json" <<'PY'
import json,time,urllib.request,urllib.error,sys
from pathlib import Path
cfg=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')); token=cfg['gateway']['auth']['token']
url='http://127.0.0.1:18789/tools/invoke'
candidates=[('session_status',{}),('sessions_list',{})]
rows=[]
for tool,args in candidates:
 body=json.dumps({'tool':tool,'args':args,'sessionKey':'main'}).encode(); req=urllib.request.Request(url,data=body,method='POST',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
 start=time.perf_counter(); status=0; ok=False
 try:
  with urllib.request.urlopen(req,timeout=10) as resp: status=resp.status; payload=json.loads(resp.read(1000000)); ok=status==200 and payload.get('ok') is True
 except urllib.error.HTTPError as e: status=e.code
 except Exception: status=0
 rows.append({'tool':tool,'status':status,'ok':ok,'duration_ms':round((time.perf_counter()-start)*1000,3)})
Path(sys.argv[2]).write_text(json.dumps({'candidates':rows,'selected':next((x['tool'] for x in rows if x['ok']),None),'secret_values_recorded':False},sort_keys=True,indent=2)+'\n')
PY
[ "$?" -eq 0 ] || fatal "baseline_safe_tool_probe_failed" "INSPECT_GATEWAY_TOOLS_INVOKE"
BASELINE_SAFE_TOOL="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("selected") or "")' "$TMP_ROOT/baseline-tool-safe.json")"
[ -n "$BASELINE_SAFE_TOOL" ] || fatal "no_safe_baseline_tool_accessible" "INSPECT_EXISTING_TOOL_POLICY"
record_check "safe_builtin_baseline" "PASS" "baseline_tool_accessible_before_enablement"
