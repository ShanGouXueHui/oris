# Cold and runtime plugin inventory.
OPENCLAW_VERSION="$(openclaw --version 2>/dev/null | head -n 1 | tr -d '\r')"
case "$OPENCLAW_VERSION" in *"$EXPECTED_OPENCLAW_VERSION"*) record_check "openclaw_version" "PASS" "expected_installed_version" ;; *) record_check "openclaw_version" "FAIL" "unexpected_runtime_version" ;; esac

openclaw plugins list --json > "$TMP_ROOT/plugins-list.json" 2> "$TMP_ROOT/plugins-list.stderr"
PLUGIN_LIST_RC="$?"
openclaw plugins inspect "$PLUGIN_ID" --runtime --json > "$TMP_ROOT/plugin-runtime.json" 2> "$TMP_ROOT/plugin-runtime.stderr"
PLUGIN_INSPECT_RC="$?"
if [ "$PLUGIN_LIST_RC" -ne 0 ] || [ "$PLUGIN_INSPECT_RC" -ne 0 ]; then
  record_check "plugin_inventory_commands" "FAIL" "plugin_list_or_runtime_inspect_failed"
else
  record_check "plugin_inventory_commands" "PASS" "cold_and_runtime_inventory_collected"
fi

python3 - "$TMP_ROOT/plugins-list.json" "$TMP_ROOT/plugin-runtime.json" "$TMP_ROOT/runtime-safe.json" "$PLUGIN_ID" "$PLUGIN_VERSION" "$TOOL_1" "$TOOL_2" "$TOOL_3" "$HOOK_1" "$HOOK_2" "$HOOK_3" <<'PY_RUNTIME'
import json,sys
from pathlib import Path
try:
 listing=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
 runtime=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
except Exception:
 Path(sys.argv[3]).write_text(json.dumps({'parse_ok':False})+'\n')
 raise SystemExit(0)
plugin_id=sys.argv[4]; version=sys.argv[5]; expected_tools=set(sys.argv[6:9]); expected_hooks=set(sys.argv[9:12])
plugins=listing.get('plugins') if isinstance(listing,dict) else []
found=False; enabled=False; errors=0; version_ok=False
if isinstance(plugins,list):
 for item in plugins:
  if not isinstance(item,dict): continue
  pid=str(item.get('id') or item.get('name') or '')
  if pid!=plugin_id: continue
  found=True; enabled=item.get('enabled') is True
  version_ok=str(item.get('version') or '')==version
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
  for k in value:
   if isinstance(k,str): target.add(k)
def walk(v):
 if isinstance(v,dict):
  for k,x in v.items():
   low=str(k).lower()
   if low in {'tools','registeredtools','toolnames'}: add(x,tools)
   elif low in {'hooks','registeredhooks','hooknames','typedhooks','customhooks'}: add(x,hooks)
   walk(x)
 elif isinstance(v,list):
  for x in v: walk(x)
walk(runtime)
write_names={x for x in tools if any(term in x.lower() for term in ('submit','cancel','retry','create','enqueue','mutate','write','delete','update'))}
payload={
 'parse_ok':True,
 'plugin_found':found,
 'plugin_enabled':enabled,
 'plugin_version_ok':version_ok,
 'plugin_error_count':errors,
 'runtime_tools':sorted(tools),
 'runtime_hooks':sorted(hooks),
 'runtime_tools_exact':tools==expected_tools,
 'runtime_hooks_exact':hooks==expected_hooks,
 'write_tools':sorted(write_names),
 'write_tools_absent':not write_names,
 'secret_values_recorded':False,
}
Path(sys.argv[3]).write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n',encoding='utf-8')
PY_RUNTIME
RUNTIME_PARSE_OK="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1])).get("parse_ok") else "NO")' "$TMP_ROOT/runtime-safe.json" 2>/dev/null || echo NO)"
if [ "$RUNTIME_PARSE_OK" = "YES" ]; then
  RUNTIME_CONTRACT_OK="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("YES" if d["plugin_found"] and d["plugin_enabled"] and d["plugin_version_ok"] and d["plugin_error_count"]==0 and d["runtime_tools_exact"] and d["runtime_hooks_exact"] else "NO")' "$TMP_ROOT/runtime-safe.json")"
  WRITE_TOOLS_ABSENT="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["write_tools_absent"] else "NO")' "$TMP_ROOT/runtime-safe.json")"
  [ "$RUNTIME_CONTRACT_OK" = "YES" ] && record_check "plugin_runtime_contract" "PASS" "exact_three_tools_three_hooks_zero_errors" || record_check "plugin_runtime_contract" "FAIL" "cold_or_runtime_contract_mismatch"
  [ "$WRITE_TOOLS_ABSENT" = "YES" ] && record_check "write_tools_absent" "PASS" "no_mutation_tool_registered" || record_check "write_tools_absent" "FAIL" "write_like_tool_detected"
else
  record_check "plugin_runtime_contract" "FAIL" "runtime_json_parse_failed"
  record_check "write_tools_absent" "FAIL" "runtime_inventory_unavailable"
  WRITE_TOOLS_ABSENT="NO"
fi

# Gateway and route health. No service operation is performed.
DIRECT_ROOT_STATUS="$(curl -sS --max-time 8 -o "$TMP_ROOT/direct-root.body" -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 8 -H 'Cache-Control: no-cache' -o "$TMP_ROOT/public-root.body" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
ADMIN_STATUS="$(curl -sS -k --max-time 8 -o /dev/null -w '%{http_code}' "https://$DOMAIN/admin" 2>/dev/null || true)"
ROLLBACK_SHELL_STATUS="$(curl -sS -k --max-time 8 -o /dev/null -w '%{http_code}' "https://$DOMAIN/_oris-chat-shell" 2>/dev/null || true)"
DIRECT_SHA="$(sha256sum "$TMP_ROOT/direct-root.body" 2>/dev/null | awk '{print $1}')"
PUBLIC_SHA="$(sha256sum "$TMP_ROOT/public-root.body" 2>/dev/null | awk '{print $1}')"
if [ "$GATEWAY_STATE_BEFORE" = "active" ] && [ "$DIRECT_ROOT_STATUS" = "200" ] && [ "$PUBLIC_ROOT_STATUS" = "200" ] && [ -n "$DIRECT_SHA" ] && [ "$DIRECT_SHA" = "$PUBLIC_SHA" ]; then
  record_check "gateway_and_public_root" "PASS" "active_direct_public_200_bodies_match"
else
  record_check "gateway_and_public_root" "FAIL" "gateway_or_public_root_contract_failed"
fi
case "$ADMIN_STATUS" in 401|403|404) record_check "restricted_admin_route" "PASS" "unauthenticated_status_$ADMIN_STATUS" ;; *) record_check "restricted_admin_route" "REVIEW" "unexpected_unauthenticated_status_$ADMIN_STATUS" ;; esac
case "$ROLLBACK_SHELL_STATUS" in 401|403|404) record_check "restricted_rollback_shell_route" "PASS" "unauthenticated_status_$ROLLBACK_SHELL_STATUS" ;; *) record_check "restricted_rollback_shell_route" "REVIEW" "unexpected_unauthenticated_status_$ROLLBACK_SHELL_STATUS" ;; esac

ENQUEUE_LOOPBACK_ONLY="$(loopback_only "$ENQUEUE_PORT")"
INTAKE_LOOPBACK_ONLY="$(loopback_only "$INTAKE_PORT")"
WEB_CONSOLE_LOOPBACK_ONLY="$(loopback_only "$WEB_CONSOLE_PORT")"
[ "$ENQUEUE_LOOPBACK_ONLY" = "YES" ] && record_check "enqueue_listener_private" "PASS" "loopback_only_18891" || record_check "enqueue_listener_private" "FAIL" "enqueue_listener_$ENQUEUE_LOOPBACK_ONLY"
[ "$INTAKE_LOOPBACK_ONLY" = "YES" ] && record_check "intake_listener_private" "PASS" "loopback_only_18892" || record_check "intake_listener_private" "FAIL" "intake_listener_$INTAKE_LOOPBACK_ONLY"
[ "$WEB_CONSOLE_LOOPBACK_ONLY" = "YES" ] && record_check "web_console_listener_private" "PASS" "loopback_only_18893" || record_check "web_console_listener_private" "REVIEW" "web_console_listener_$WEB_CONSOLE_LOOPBACK_ONLY"

