# Parse current OpenClaw policy into a secret-free structural summary.
python3 - "$OPENCLAW_CONFIG" "$TMP_ROOT/config-safe.json" "$PLUGIN_ID" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY_CONFIG'
import hashlib, json, os, re, sys
from pathlib import Path
path=Path(sys.argv[1]); out=Path(sys.argv[2]); plugin_id=sys.argv[3]; approved=set(sys.argv[4:7])
data=json.loads(path.read_text(encoding='utf-8'))

def string_list(value):
 return value if isinstance(value,list) and all(isinstance(x,str) for x in value) else None

def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def safe_profile(value):
 return value[:80] if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}',value) else None

gateway=data.get('gateway') if isinstance(data.get('gateway'),dict) else {}
auth=gateway.get('auth') if isinstance(gateway.get('auth'),dict) else {}
mode=auth.get('mode') or 'token'
tools=data.get('tools') if isinstance(data.get('tools'),dict) else {}
allow=string_list(tools.get('allow')); deny=string_list(tools.get('deny'))
plugins=data.get('plugins') if isinstance(data.get('plugins'),dict) else {}
entries=plugins.get('entries') if isinstance(plugins.get('entries'),dict) else {}
conversation_access=[]
for key,value in entries.items():
 if not isinstance(key,str) or not isinstance(value,dict): continue
 hooks=value.get('hooks') if isinstance(value.get('hooks'),dict) else {}
 if hooks.get('allowConversationAccess') is True: conversation_access.append(key)
entry=entries.get(plugin_id) if isinstance(entries.get(plugin_id),dict) else {}
plugin_cfg=entry.get('config') if isinstance(entry.get('config'),dict) else {}
telemetry_path=plugin_cfg.get('telemetryPath') if isinstance(plugin_cfg.get('telemetryPath'),str) else '~/.local/state/oris/openclaw-plugin/latency.jsonl'
telemetry_enabled=plugin_cfg.get('telemetryEnabled') is not False
telemetry_max=plugin_cfg.get('telemetryMaxBytes') if isinstance(plugin_cfg.get('telemetryMaxBytes'),int) else 5242880
base_url=plugin_cfg.get('baseUrl') if isinstance(plugin_cfg.get('baseUrl'),str) else 'http://127.0.0.1:18891'
request_timeout=plugin_cfg.get('requestTimeoutMs') if isinstance(plugin_cfg.get('requestTimeoutMs'),int) else 5000
agents=data.get('agents') if isinstance(data.get('agents'),dict) else {}
agent_records=[]

def append_agent_record(scope, identity, item):
 if not isinstance(item,dict): return
 agent_tools=item.get('tools') if isinstance(item.get('tools'),dict) else {}
 a_allow=string_list(agent_tools.get('allow')); a_deny=string_list(agent_tools.get('deny'))
 agent_records.append({
  'scope':scope,
  'agent_id_hash':hashlib.sha256(identity.encode()).hexdigest() if identity else None,
  'allow_present':a_allow is not None,
  'allow_count':len(a_allow or []),
  'allow_sha256':digest(a_allow) if a_allow is not None else None,
  'approved_in_allow':sorted(approved.intersection(a_allow or [])),
  'deny_present':a_deny is not None,
  'deny_count':len(a_deny or []),
  'approved_in_deny':sorted(approved.intersection(a_deny or [])),
  'profile':safe_profile(agent_tools.get('profile')),
 })

append_agent_record('defaults','',agents.get('defaults'))
raw_agent_list=agents.get('list') if isinstance(agents.get('list'),list) else []
for item in raw_agent_list:
 if not isinstance(item,dict): continue
 agent_id=str(item.get('id') or item.get('name') or '')
 append_agent_record('list',agent_id,item)
for key,item in agents.items():
 if key in {'defaults','list'} or not isinstance(key,str) or not isinstance(item,dict): continue
 if isinstance(item.get('tools'),dict): append_agent_record('named_map',key,item)
payload={
 'config_owner_ok':path.stat().st_uid==os.getuid(),
 'config_mode_ok':(path.stat().st_mode & 0o777)==0o600,
 'auth_mode':mode if mode=='token' else 'unsupported',
 'auth_credential_key_present':mode in auth,
 'global_allow_present':allow is not None,
 'global_allow_count':len(allow or []),
 'global_allow_sha256':digest(allow) if allow is not None else None,
 'approved_in_global_allow':sorted(approved.intersection(allow or [])),
 'global_deny_present':deny is not None,
 'global_deny_count':len(deny or []),
 'approved_in_global_deny':sorted(approved.intersection(deny or [])),
 'global_profile':safe_profile(tools.get('profile')),
 'agent_policy_records':agent_records,
 'conversation_access_plugins':conversation_access,
 'conversation_access_scoped_exactly':conversation_access==[plugin_id],
 'plugin_entry_enabled':entry.get('enabled') is True,
 'telemetry_enabled':telemetry_enabled,
 'telemetry_path':telemetry_path,
 'telemetry_max_bytes':telemetry_max,
 'base_url':base_url,
 'request_timeout_ms':request_timeout,
 'secret_values_recorded':False,
}
out.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n',encoding='utf-8')
PY_CONFIG
if [ "$?" -ne 0 ]; then
  fatal "openclaw_config_safe_parse_failed" "INSPECT_OPENCLAW_CONFIG_WITHOUT_PRINTING_CONTENT"
fi

CONFIG_MODE_OK="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("YES" if d["config_owner_ok"] and d["config_mode_ok"] else "NO")' "$TMP_ROOT/config-safe.json")"
AUTH_MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["auth_mode"])' "$TMP_ROOT/config-safe.json")"
AUTH_PRESENT="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["auth_credential_key_present"] else "NO")' "$TMP_ROOT/config-safe.json")"
DENIED_APPROVED_COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["approved_in_global_deny"]))' "$TMP_ROOT/config-safe.json")"
CONVERSATION_SCOPED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["conversation_access_scoped_exactly"] else "NO")' "$TMP_ROOT/config-safe.json")"
PLUGIN_ENTRY_ENABLED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["plugin_entry_enabled"] else "NO")' "$TMP_ROOT/config-safe.json")"
BASE_URL="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_url"])' "$TMP_ROOT/config-safe.json")"

[ "$CONFIG_MODE_OK" = "YES" ] && record_check "openclaw_config_permissions" "PASS" "owner_admin_mode_0600" || record_check "openclaw_config_permissions" "FAIL" "owner_or_mode_mismatch"
if [ "$AUTH_MODE" = "token" ] && [ "$AUTH_PRESENT" = "YES" ]; then record_check "gateway_auth_policy" "PASS" "token_mode_credential_key_present_value_not_read"; else record_check "gateway_auth_policy" "FAIL" "unexpected_auth_mode_or_missing_secret"; fi
[ "$DENIED_APPROVED_COUNT" = "3" ] && record_check "approved_tools_currently_denied" "PASS" "all_three_names_in_global_deny" || record_check "approved_tools_currently_denied" "FAIL" "approved_deny_contract_mismatch"
[ "$CONVERSATION_SCOPED" = "YES" ] && record_check "conversation_access_scope" "PASS" "scoped_only_to_oris_plugin" || record_check "conversation_access_scope" "FAIL" "conversation_access_not_exactly_scoped"
[ "$PLUGIN_ENTRY_ENABLED" = "YES" ] && record_check "plugin_config_enabled" "PASS" "plugin_entry_enabled" || record_check "plugin_config_enabled" "FAIL" "plugin_entry_not_enabled"
[ "$BASE_URL" = "http://127.0.0.1:18891" ] && record_check "plugin_loopback_base_url" "PASS" "expected_loopback_status_api" || record_check "plugin_loopback_base_url" "FAIL" "unexpected_plugin_base_url"

POLICY_AMBIGUITY="$(python3 - "$TMP_ROOT/config-safe.json" <<'PY_POLICY'
import json,sys
d=json.load(open(sys.argv[1]))
reasons=[]
if d['global_allow_present'] and len(d['approved_in_global_allow']) not in {0,3}: reasons.append('partial_global_allow')
for a in d['agent_policy_records']:
 if a['allow_present'] and len(a['approved_in_allow']) not in {0,3}: reasons.append('partial_agent_allow')
 if a['approved_in_deny']: reasons.append('agent_specific_deny')
print(','.join(sorted(set(reasons))) or 'NONE')
PY_POLICY
)"
if [ "$POLICY_AMBIGUITY" = "NONE" ]; then record_check "allow_profile_agent_policy_discovery" "PASS" "policy_shape_captured_no_partial_or_agent_deny"; else record_check "allow_profile_agent_policy_discovery" "REVIEW" "$POLICY_AMBIGUITY"; fi

