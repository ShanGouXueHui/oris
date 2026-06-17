#!/usr/bin/env bash

TASK_ID="commercial-openclaw-tool-plugin-discovery-20260617"
PREVIOUS_TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_SERVICE="openclaw-gateway.service"
OPENCLAW_PORT="18789"
INTAKE_PORT="18892"
CONSOLE_PORT="18893"
DOMAIN="control.orisfy.com"
EXPECTED_PRODUCT_COMMIT="bcb93e17ea88704548101f5e4a5c460e15a80ec7"
EXPECTED_ORIS_COMPLETION_COMMIT="54d7f1dd94754d57a35cda90211aa9eea0620a12"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-plugin-discovery-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/discovery.log"
RESULT_JSON="$TMP_ROOT/discovery.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_tool_plugin_discovery"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/openclaw-tool-plugin-latency-discovery-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/openclaw-tool-plugin-latency-discovery-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
DISCOVERY_COMPLETE="NO"
OPENCLAW_VERSION="unknown"
NODE_VERSION="unknown"
OPENCLAW_SERVICE_STATE="unknown"
OPENCLAW_DIRECT_STATUS="000"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ROOT_MATCHES_DIRECT="NO"
PLUGIN_CLI_SUPPORTED="NO"
PLUGIN_LIST_RC="unknown"
PLUGIN_INSPECT_COLD_RC="unknown"
PLUGIN_INSPECT_RUNTIME_RC="unknown"
PLUGIN_DOCTOR_RC="unknown"
PLUGIN_TOTAL_COUNT="unknown"
PLUGIN_ENABLED_COUNT="unknown"
PLUGIN_ERROR_COUNT="unknown"
EXISTING_ORIS_PLUGIN_COUNT="unknown"
REGISTERED_TOOL_COUNT="unknown"
REGISTERED_HOOK_COUNT="unknown"
TOOL_PLUGIN_SDK_SUPPORTED="NO"
PLUGIN_ENTRY_SDK_SUPPORTED="NO"
AGENT_END_HOOK_SUPPORTED="NO"
MODEL_CALL_HOOKS_SUPPORTED="NO"
AFTER_TOOL_CALL_HOOK_SUPPORTED="NO"
PLUGIN_POLICY_MODE="unknown"
TOOLS_POLICY_MODE="unknown"
HARNESS_SERVICE_COUNT="unknown"
HARNESS_ACTIVE_COUNT="unknown"
ORIS_CANDIDATE_ROUTE_COUNT="unknown"
ORIS_INTEGRATION_FILE_COUNT="unknown"
SESSION_RUNTIME_SAMPLE_COUNT="unknown"
JOURNAL_AGENT_END_COUNT="unknown"
JOURNAL_MODEL_CALL_ENDED_COUNT="unknown"
JOURNAL_TOOL_DURATION_COUNT="unknown"
PUBLIC_HTTP_SAMPLE_COUNT="0"
PUBLIC_HTTP_MEDIAN_TTFB_MS="unknown"
PUBLIC_HTTP_MEDIAN_TOTAL_MS="unknown"
DIRECT_HTTP_MEDIAN_TTFB_MS="unknown"
DIRECT_HTTP_MEDIAN_TOTAL_MS="unknown"
LATENCY_OBSERVABILITY_PATH="unknown"
RECOMMENDED_PLUGIN_SHAPE="unknown"
ACTIVE_QUEUE_COUNT="unknown"
INTAKE_LOOPBACK_ONLY="unknown"
PRODUCT_BASELINE_PRESERVED="NO"
CONFIG_OR_SERVICE_CHANGED="NO"
PRODUCT_TASK_SUBMITTED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_OPENCLAW_TOOL_PLUGIN_DISCOVERY_FAILURE"

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
  echo "PREVIOUS_TASK_ID=$PREVIOUS_TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "DISCOVERY_COMPLETE=$DISCOVERY_COMPLETE"
  echo "OPENCLAW_VERSION=$OPENCLAW_VERSION"
  echo "NODE_VERSION=$NODE_VERSION"
  echo "OPENCLAW_SERVICE_STATE=$OPENCLAW_SERVICE_STATE"
  echo "OPENCLAW_DIRECT_STATUS=$OPENCLAW_DIRECT_STATUS"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ROOT_MATCHES_DIRECT=$PUBLIC_ROOT_MATCHES_DIRECT"
  echo "PLUGIN_CLI_SUPPORTED=$PLUGIN_CLI_SUPPORTED"
  echo "PLUGIN_LIST_RC=$PLUGIN_LIST_RC"
  echo "PLUGIN_INSPECT_COLD_RC=$PLUGIN_INSPECT_COLD_RC"
  echo "PLUGIN_INSPECT_RUNTIME_RC=$PLUGIN_INSPECT_RUNTIME_RC"
  echo "PLUGIN_DOCTOR_RC=$PLUGIN_DOCTOR_RC"
  echo "PLUGIN_TOTAL_COUNT=$PLUGIN_TOTAL_COUNT"
  echo "PLUGIN_ENABLED_COUNT=$PLUGIN_ENABLED_COUNT"
  echo "PLUGIN_ERROR_COUNT=$PLUGIN_ERROR_COUNT"
  echo "EXISTING_ORIS_PLUGIN_COUNT=$EXISTING_ORIS_PLUGIN_COUNT"
  echo "REGISTERED_TOOL_COUNT=$REGISTERED_TOOL_COUNT"
  echo "REGISTERED_HOOK_COUNT=$REGISTERED_HOOK_COUNT"
  echo "TOOL_PLUGIN_SDK_SUPPORTED=$TOOL_PLUGIN_SDK_SUPPORTED"
  echo "PLUGIN_ENTRY_SDK_SUPPORTED=$PLUGIN_ENTRY_SDK_SUPPORTED"
  echo "AGENT_END_HOOK_SUPPORTED=$AGENT_END_HOOK_SUPPORTED"
  echo "MODEL_CALL_HOOKS_SUPPORTED=$MODEL_CALL_HOOKS_SUPPORTED"
  echo "AFTER_TOOL_CALL_HOOK_SUPPORTED=$AFTER_TOOL_CALL_HOOK_SUPPORTED"
  echo "PLUGIN_POLICY_MODE=$PLUGIN_POLICY_MODE"
  echo "TOOLS_POLICY_MODE=$TOOLS_POLICY_MODE"
  echo "HARNESS_SERVICE_COUNT=$HARNESS_SERVICE_COUNT"
  echo "HARNESS_ACTIVE_COUNT=$HARNESS_ACTIVE_COUNT"
  echo "ORIS_CANDIDATE_ROUTE_COUNT=$ORIS_CANDIDATE_ROUTE_COUNT"
  echo "ORIS_INTEGRATION_FILE_COUNT=$ORIS_INTEGRATION_FILE_COUNT"
  echo "SESSION_RUNTIME_SAMPLE_COUNT=$SESSION_RUNTIME_SAMPLE_COUNT"
  echo "JOURNAL_AGENT_END_COUNT=$JOURNAL_AGENT_END_COUNT"
  echo "JOURNAL_MODEL_CALL_ENDED_COUNT=$JOURNAL_MODEL_CALL_ENDED_COUNT"
  echo "JOURNAL_TOOL_DURATION_COUNT=$JOURNAL_TOOL_DURATION_COUNT"
  echo "PUBLIC_HTTP_SAMPLE_COUNT=$PUBLIC_HTTP_SAMPLE_COUNT"
  echo "PUBLIC_HTTP_MEDIAN_TTFB_MS=$PUBLIC_HTTP_MEDIAN_TTFB_MS"
  echo "PUBLIC_HTTP_MEDIAN_TOTAL_MS=$PUBLIC_HTTP_MEDIAN_TOTAL_MS"
  echo "DIRECT_HTTP_MEDIAN_TTFB_MS=$DIRECT_HTTP_MEDIAN_TTFB_MS"
  echo "DIRECT_HTTP_MEDIAN_TOTAL_MS=$DIRECT_HTTP_MEDIAN_TOTAL_MS"
  echo "LATENCY_OBSERVABILITY_PATH=$LATENCY_OBSERVABILITY_PATH"
  echo "RECOMMENDED_PLUGIN_SHAPE=$RECOMMENDED_PLUGIN_SHAPE"
  echo "ACTIVE_QUEUE_COUNT=$ACTIVE_QUEUE_COUNT"
  echo "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "CONFIG_OR_SERVICE_CHANGED=$CONFIG_OR_SERVICE_CHANGED"
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

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user" "RUN_AS_ADMIN"; fi
for cmd in git curl python3 sha256sum systemctl ss find grep awk sed readlink journalctl; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$OPENCLAW_CONFIG" ] || fail_now "openclaw_config_missing" "RESTORE_OPENCLAW_CONFIG"
OPENCLAW_BIN="$(command -v openclaw 2>/dev/null || true)"
[ -n "$OPENCLAW_BIN" ] || fail_now "openclaw_binary_missing" "RESTORE_EXISTING_OPENCLAW_INSTALLATION"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "PREVIOUS_TASK_ID=$PREVIOUS_TASK_ID"
log "MODE=READ_ONLY_OPENCLAW_TOOL_PLUGIN_AND_LATENCY_DISCOVERY"
log "CONFIG_OR_SERVICE_CHANGED=NO"
log "PRODUCT_TASK_SUBMITTED=NO"
log "PRODUCT_REPOSITORY_MUTATED=NO"
log "OPENCLAW_REINSTALLED_OR_UPGRADED=NO"
log "SECRET_VALUES_RECORDED=NO"

ORIS_REMOTE_MAIN_BEFORE="$(git -C "$ORIS_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
OPENCLAW_CONFIG_HASH_BEFORE="$(sha256sum "$OPENCLAW_CONFIG" | awk '{print $1}')"
OPENCLAW_SERVICE_MAINPID_BEFORE="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"

[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_head" "REVIEW_COMPLETED_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_remote_main" "REVIEW_COMPLETED_PRODUCT_BASELINE"
[ -z "$PRODUCT_STATUS_BEFORE" ] || fail_now "product_worktree_not_clean" "REVIEW_COMPLETED_PRODUCT_BASELINE"
if [ "$ORIS_REMOTE_MAIN_BEFORE" != "$EXPECTED_ORIS_COMPLETION_COMMIT" ]; then
  log "ORIS_REMOTE_MAIN_ADVANCED_SINCE_COMPLETION=$ORIS_REMOTE_MAIN_BEFORE"
fi

ACTIVE_QUEUE_COUNT="$(find "$ORIS_REPO/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' -o -name '*.claimed.json' -o -name '*.planning.json' -o -name '*.executing.json' -o -name '*.committing.json' -o -name '*.pushing.json' -o -name '*.cancelling.json' \) 2>/dev/null | wc -l | tr -d ' ')"
[ "$ACTIVE_QUEUE_COUNT" = "0" ] || fail_now "active_queue_present" "WAIT_FOR_QUEUE_TO_DRAIN"

OPENCLAW_VERSION="$($OPENCLAW_BIN --version 2>/dev/null | head -n 1 | tr -d '\r' || true)"
NODE_VERSION="$(node --version 2>/dev/null || echo unavailable)"
OPENCLAW_SERVICE_STATE="$(systemctl --user is-active "$OPENCLAW_SERVICE" 2>/dev/null || true)"
OPENCLAW_DIRECT_STATUS="$(curl -sS --max-time 10 -o "$TMP_ROOT/direct-root.body" -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 10 -H 'Cache-Control: no-cache' -o "$TMP_ROOT/public-root.body" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
DIRECT_SHA="$(sha256sum "$TMP_ROOT/direct-root.body" 2>/dev/null | awk '{print $1}')"
PUBLIC_SHA="$(sha256sum "$TMP_ROOT/public-root.body" 2>/dev/null | awk '{print $1}')"
if [ "$OPENCLAW_DIRECT_STATUS" = "200" ] && [ "$PUBLIC_ROOT_STATUS" = "200" ] && [ -n "$DIRECT_SHA" ] && [ "$DIRECT_SHA" = "$PUBLIC_SHA" ]; then PUBLIC_ROOT_MATCHES_DIRECT="YES"; fi
[ "$OPENCLAW_SERVICE_STATE" = "active" ] || fail_now "openclaw_gateway_not_active" "RESTORE_OPENCLAW_GATEWAY"
[ "$PUBLIC_ROOT_MATCHES_DIRECT" = "YES" ] || fail_now "public_root_not_native_openclaw" "RESTORE_NATIVE_OPENCLAW_ROUTE"

INTAKE_LISTENER="$(ss -ltn 2>/dev/null | awk -v p=":$INTAKE_PORT" '$4 ~ p"$" {print $4; exit}')"
case "$INTAKE_LISTENER" in 127.0.0.1:*|\[::1\]:*) INTAKE_LOOPBACK_ONLY="YES" ;; *) INTAKE_LOOPBACK_ONLY="NO" ;; esac
[ "$INTAKE_LOOPBACK_ONLY" = "YES" ] || fail_now "intake_not_loopback_only" "RESTORE_INTAKE_PRIVATE_BINDING"

$OPENCLAW_BIN --help > "$TMP_ROOT/openclaw-help.txt" 2>&1 || true
$OPENCLAW_BIN plugins --help > "$TMP_ROOT/plugins-help.txt" 2>&1
PLUGINS_HELP_RC="$?"
if [ "$PLUGINS_HELP_RC" -eq 0 ] && grep -qE '(^|[[:space:]])plugins([[:space:]]|$)|Manage OpenClaw plugins' "$TMP_ROOT/plugins-help.txt"; then PLUGIN_CLI_SUPPORTED="YES"; fi

$OPENCLAW_BIN plugins list --json > "$TMP_ROOT/plugins-list.json" 2> "$TMP_ROOT/plugins-list.err"
PLUGIN_LIST_RC="$?"
$OPENCLAW_BIN plugins inspect --all --json > "$TMP_ROOT/plugins-inspect-cold.json" 2> "$TMP_ROOT/plugins-inspect-cold.err"
PLUGIN_INSPECT_COLD_RC="$?"
$OPENCLAW_BIN plugins inspect --all --runtime --json > "$TMP_ROOT/plugins-inspect-runtime.json" 2> "$TMP_ROOT/plugins-inspect-runtime.err"
PLUGIN_INSPECT_RUNTIME_RC="$?"
$OPENCLAW_BIN plugins doctor > "$TMP_ROOT/plugins-doctor.txt" 2>&1
PLUGIN_DOCTOR_RC="$?"
$OPENCLAW_BIN gateway status --deep --require-rpc > "$TMP_ROOT/gateway-status.txt" 2>&1
GATEWAY_DEEP_STATUS_RC="$?"

[ "$PLUGIN_CLI_SUPPORTED" = "YES" ] || fail_now "plugin_cli_not_supported" "REVIEW_INSTALLED_OPENCLAW_VERSION"
[ "$PLUGIN_LIST_RC" = "0" ] || fail_now "plugin_list_failed" "INSPECT_PLUGIN_DISCOVERY_ERRORS"

python3 - "$TMP_ROOT/plugins-list.json" "$TMP_ROOT/plugins-inspect-runtime.json" "$TMP_ROOT/plugin-summary.json" <<'PY_PLUGIN_SUMMARY'
import json,re,sys
from pathlib import Path

list_path=Path(sys.argv[1]); runtime_path=Path(sys.argv[2]); out=Path(sys.argv[3])
listing=json.loads(list_path.read_text(encoding='utf-8'))
plugins=listing.get('plugins') if isinstance(listing,dict) else []
if not isinstance(plugins,list): plugins=[]
ids=[]; enabled=0; errors=0; oris=[]
for item in plugins:
    if not isinstance(item,dict): continue
    pid=str(item.get('id') or item.get('name') or '')
    ids.append(pid)
    if item.get('enabled') is True: enabled+=1
    if item.get('status')=='error' or item.get('error'): errors+=1
    if 'oris' in pid.lower() or 'oris' in str(item.get('name') or '').lower(): oris.append(pid)

runtime=None
try:
    runtime=json.loads(runtime_path.read_text(encoding='utf-8'))
except Exception:
    runtime=None

tools=set(); hooks=set(); services=set(); methods=set()
def add_names(value,target):
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
            if low in {'tools','registeredtools','toolnames'}: add_names(child,tools)
            elif low in {'hooks','registeredhooks','hooknames'}: add_names(child,hooks)
            elif low in {'services','registeredservices'}: add_names(child,services)
            elif low in {'gatewaymethods','methods','registeredgatewaymethods'}: add_names(child,methods)
            walk(child)
    elif isinstance(value,list):
        for child in value: walk(child)
if runtime is not None: walk(runtime)

payload={
  'plugin_total_count':len(plugins),
  'plugin_enabled_count':enabled,
  'plugin_error_count':errors,
  'plugin_ids':sorted(x for x in ids if x),
  'existing_oris_plugin_ids':sorted(oris),
  'registered_tools':sorted(tools),
  'registered_hooks':sorted(hooks),
  'registered_services':sorted(services),
  'registered_gateway_methods':sorted(methods),
  'runtime_json_available':runtime is not None,
  'secret_values_recorded':False,
}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_PLUGIN_SUMMARY
[ "$?" -eq 0 ] || fail_now "plugin_summary_parse_failed" "INSPECT_PLUGIN_JSON_FORMAT"
PLUGIN_TOTAL_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["plugin_total_count"])' "$TMP_ROOT/plugin-summary.json")"
PLUGIN_ENABLED_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["plugin_enabled_count"])' "$TMP_ROOT/plugin-summary.json")"
PLUGIN_ERROR_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["plugin_error_count"])' "$TMP_ROOT/plugin-summary.json")"
EXISTING_ORIS_PLUGIN_COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["existing_oris_plugin_ids"]))' "$TMP_ROOT/plugin-summary.json")"
REGISTERED_TOOL_COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["registered_tools"]))' "$TMP_ROOT/plugin-summary.json")"
REGISTERED_HOOK_COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["registered_hooks"]))' "$TMP_ROOT/plugin-summary.json")"

python3 - "$OPENCLAW_CONFIG" "$TMP_ROOT/config-safe.json" <<'PY_CONFIG_SAFE'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]); out=Path(sys.argv[2]); data=json.loads(p.read_text(encoding='utf-8'))
plugins=data.get('plugins') if isinstance(data.get('plugins'),dict) else {}
tools=data.get('tools') if isinstance(data.get('tools'),dict) else {}
entries=plugins.get('entries') if isinstance(plugins.get('entries'),dict) else {}
entry_safe=[]
for pid,value in sorted(entries.items()):
    item=value if isinstance(value,dict) else {}
    config=item.get('config') if isinstance(item.get('config'),dict) else {}
    hooks=item.get('hooks') if isinstance(item.get('hooks'),dict) else {}
    entry_safe.append({
      'id':pid,
      'enabled':item.get('enabled'),
      'config_keys':sorted(str(k) for k in config.keys()),
      'hook_config_keys':sorted(str(k) for k in hooks.keys()),
    })
load=plugins.get('load') if isinstance(plugins.get('load'),dict) else {}
paths=load.get('paths') if isinstance(load.get('paths'),list) else []
def names(value):
    return sorted(str(x) for x in value) if isinstance(value,list) else []
payload={
 'plugins_enabled':plugins.get('enabled',True),
 'plugins_allow':names(plugins.get('allow')),
 'plugins_deny':names(plugins.get('deny')),
 'plugin_load_path_count':len(paths),
 'plugin_load_path_hashes':[hashlib.sha256(str(x).encode()).hexdigest() for x in paths],
 'plugin_entries':entry_safe,
 'plugin_slots':sorted(str(k) for k in (plugins.get('slots') or {}).keys()) if isinstance(plugins.get('slots'),dict) else [],
 'tools_allow':names(tools.get('allow')),
 'tools_deny':names(tools.get('deny')),
 'tools_profile':tools.get('profile') if isinstance(tools.get('profile'),str) else None,
 'secret_values_recorded':False,
}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_CONFIG_SAFE
[ "$?" -eq 0 ] || fail_now "openclaw_config_safe_parse_failed" "INSPECT_OPENCLAW_CONFIG_STRUCTURE"
PLUGIN_POLICY_MODE="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("disabled" if not d["plugins_enabled"] else ("allowlist" if d["plugins_allow"] else "default"))' "$TMP_ROOT/config-safe.json")"
TOOLS_POLICY_MODE="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("allowlist" if d["tools_allow"] else ("denylist" if d["tools_deny"] else (d["tools_profile"] or "default")))' "$TMP_ROOT/config-safe.json")"

RESOLVED_BIN="$(readlink -f "$OPENCLAW_BIN" 2>/dev/null || echo "$OPENCLAW_BIN")"
python3 - "$RESOLVED_BIN" "$TMP_ROOT/package-safe.json" <<'PY_PACKAGE_SAFE'
import json,os,sys
from pathlib import Path
start=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2])
candidates=[start.parent,*start.parents]
package=None; root=None
for parent in candidates:
    p=parent/'package.json'
    if not p.is_file(): continue
    try: data=json.loads(p.read_text(encoding='utf-8'))
    except Exception: continue
    if data.get('name')=='openclaw': package=data; root=parent; break
if package is None:
    out.write_text(json.dumps({'found':False,'secret_values_recorded':False},indent=2)+'\n')
    raise SystemExit(0)
exports=package.get('exports')
keys=set(exports.keys()) if isinstance(exports,dict) else set()
def exists_or_export(subpath,relative_candidates):
    if subpath in keys: return True
    return any((root/rel).exists() for rel in relative_candidates)
payload={
 'found':True,
 'root':str(root),
 'version':package.get('version'),
 'tool_plugin_export':exists_or_export('./plugin-sdk/tool-plugin',['dist/plugin-sdk/tool-plugin.js','src/plugin-sdk/tool-plugin.ts']),
 'plugin_entry_export':exists_or_export('./plugin-sdk/plugin-entry',['dist/plugin-sdk/plugin-entry.js','src/plugin-sdk/plugin-entry.ts']),
 'package_exports_count':len(keys),
 'secret_values_recorded':False,
}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_PACKAGE_SAFE
[ "$?" -eq 0 ] || fail_now "openclaw_package_inspection_failed" "INSPECT_OPENCLAW_BINARY_LAYOUT"
OPENCLAW_PACKAGE_ROOT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("root") or "")' "$TMP_ROOT/package-safe.json")"
TOOL_PLUGIN_SDK_SUPPORTED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1])).get("tool_plugin_export") else "NO")' "$TMP_ROOT/package-safe.json")"
PLUGIN_ENTRY_SDK_SUPPORTED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1])).get("plugin_entry_export") else "NO")' "$TMP_ROOT/package-safe.json")"
if grep -qE '(^|[[:space:]])init([[:space:]]|$)' "$TMP_ROOT/plugins-help.txt" && grep -qE '(^|[[:space:]])build([[:space:]]|$)' "$TMP_ROOT/plugins-help.txt" && grep -qE '(^|[[:space:]])validate([[:space:]]|$)' "$TMP_ROOT/plugins-help.txt"; then
  AUTHORING_CLI_SUPPORTED="YES"
else
  AUTHORING_CLI_SUPPORTED="NO"
fi

if [ -n "$OPENCLAW_PACKAGE_ROOT" ] && [ -d "$OPENCLAW_PACKAGE_ROOT" ]; then
  HOOK_SCAN_FILES="$(find "$OPENCLAW_PACKAGE_ROOT" -type f \( -name '*.js' -o -name '*.mjs' -o -name '*.cjs' -o -name '*.d.ts' -o -name '*.ts' \) 2>/dev/null | head -n 20000)"
  if printf '%s\n' "$HOOK_SCAN_FILES" | xargs -r grep -l 'agent_end' 2>/dev/null | head -n 1 | grep -q .; then AGENT_END_HOOK_SUPPORTED="YES"; fi
  if printf '%s\n' "$HOOK_SCAN_FILES" | xargs -r grep -l 'model_call_started' 2>/dev/null | head -n 1 | grep -q . && printf '%s\n' "$HOOK_SCAN_FILES" | xargs -r grep -l 'model_call_ended' 2>/dev/null | head -n 1 | grep -q .; then MODEL_CALL_HOOKS_SUPPORTED="YES"; fi
  if printf '%s\n' "$HOOK_SCAN_FILES" | xargs -r grep -l 'after_tool_call' 2>/dev/null | head -n 1 | grep -q .; then AFTER_TOOL_CALL_HOOK_SUPPORTED="YES"; fi
fi

systemctl --user list-units --all --type=service --no-legend --no-pager > "$TMP_ROOT/user-services.txt" 2>/dev/null || true
python3 - "$TMP_ROOT/user-services.txt" "$TMP_ROOT/services-safe.json" <<'PY_SERVICES'
import json,re,sys
from pathlib import Path
lines=Path(sys.argv[1]).read_text(encoding='utf-8',errors='replace').splitlines()
items=[]
for line in lines:
    m=re.match(r'\s*([^\s]+\.service)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+(.*)$',line)
    if not m: continue
    unit,load,active,sub,desc=m.groups()
    low=(unit+' '+desc).lower()
    if any(k in low for k in ('oris','openclaw','harness','bridge','intake','console')):
        items.append({'unit':unit,'load':load,'active':active,'sub':sub,'description':desc[:160]})
payload={'services':items,'matching_count':len(items),'active_count':sum(1 for x in items if x['active']=='active'),'secret_values_recorded':False}
Path(sys.argv[2]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_SERVICES
HARNESS_SERVICE_COUNT="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(sum(1 for x in d["services"] if "harness" in (x["unit"]+" "+x["description"]).lower()))' "$TMP_ROOT/services-safe.json")"
HARNESS_ACTIVE_COUNT="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(sum(1 for x in d["services"] if "harness" in (x["unit"]+" "+x["description"]).lower() and x["active"]=="active"))' "$TMP_ROOT/services-safe.json")"

python3 - "$ORIS_REPO" "$TMP_ROOT/oris-integration-safe.json" <<'PY_ORIS_SCAN'
import hashlib,json,re,sys
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2])
exclude={'.git','node_modules','.venv','venv','logs','run','__pycache__'}
files=[]; routes=set(); ports=set(); service_terms=set()
route_patterns=[
 re.compile(r'@\w+\.(?:get|post|put|patch|delete|options)\(\s*["\']([^"\']+)["\']'),
 re.compile(r'(?:route|path)\s*[=:]\s*["\'](/[^"\']+)["\']'),
 re.compile(r'add_route\(\s*["\']([^"\']+)["\']'),
]
for p in root.rglob('*'):
    if not p.is_file() or any(part in exclude for part in p.parts): continue
    if p.suffix.lower() not in {'.py','.js','.ts','.mjs','.cjs','.json','.yaml','.yml','.service','.sh','.md'}: continue
    try: text=p.read_text(encoding='utf-8',errors='replace')
    except Exception: continue
    low=text.lower()
    if not any(term in low for term in ('harness','openclaw','intake','bridge','task status','task_status','cancel','retry','evidence')): continue
    rel=str(p.relative_to(root))
    files.append({'path':rel,'sha256':hashlib.sha256(text.encode()).hexdigest()})
    for pattern in route_patterns:
        for match in pattern.finditer(text):
            route=match.group(1)
            if route.startswith('/') and len(route)<180: routes.add(route)
    for port in re.findall(r'(?<!\d)(18(?:7|8|9)\d{2})(?!\d)',text): ports.add(int(port))
    for term in ('submit','status','cancel','retry','evidence','projects','queue','lease','heartbeat'):
        if term in low: service_terms.add(term)
payload={
 'integration_files':sorted(files,key=lambda x:x['path'])[:200],
 'integration_file_count':len(files),
 'candidate_routes':sorted(routes),
 'candidate_route_count':len(routes),
 'referenced_ports':sorted(ports),
 'capability_terms':sorted(service_terms),
 'secret_values_recorded':False,
}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_ORIS_SCAN
[ "$?" -eq 0 ] || fail_now "oris_integration_scan_failed" "INSPECT_ORIS_REPOSITORY_FILES"
ORIS_CANDIDATE_ROUTE_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["candidate_route_count"])' "$TMP_ROOT/oris-integration-safe.json")"
ORIS_INTEGRATION_FILE_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["integration_file_count"])' "$TMP_ROOT/oris-integration-safe.json")"

$OPENCLAW_BIN sessions --all-agents --limit all --json > "$TMP_ROOT/sessions.json" 2> "$TMP_ROOT/sessions.err"
SESSIONS_RC="$?"
if [ "$SESSIONS_RC" -ne 0 ]; then
  $OPENCLAW_BIN sessions --all-agents --json > "$TMP_ROOT/sessions.json" 2> "$TMP_ROOT/sessions.err"
  SESSIONS_RC="$?"
fi
if [ "$SESSIONS_RC" -ne 0 ]; then
  $OPENCLAW_BIN sessions --json > "$TMP_ROOT/sessions.json" 2> "$TMP_ROOT/sessions.err"
  SESSIONS_RC="$?"
fi
python3 - "$TMP_ROOT/sessions.json" "$TMP_ROOT/session-latency-safe.json" <<'PY_SESSION_LATENCY'
import json,statistics,sys
from pathlib import Path
source=Path(sys.argv[1]); out=Path(sys.argv[2])
try: data=json.loads(source.read_text(encoding='utf-8'))
except Exception: data={}
values=[]
def walk(v):
    if isinstance(v,dict):
        for k,x in v.items():
            if str(k).lower() in {'runtimems','durationms','elapsedms'} and isinstance(x,(int,float)) and x>=0:
                values.append(float(x))
            walk(x)
    elif isinstance(v,list):
        for x in v: walk(x)
walk(data)
payload={'sample_count':len(values),'median_ms':statistics.median(values) if values else None,'max_ms':max(values) if values else None,'secret_values_recorded':False}
out.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
PY_SESSION_LATENCY
SESSION_RUNTIME_SAMPLE_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sample_count"])' "$TMP_ROOT/session-latency-safe.json")"

journalctl --user -u "$OPENCLAW_SERVICE" --since '-12 hours' --no-pager -o cat > "$TMP_ROOT/gateway-journal.raw" 2>/dev/null || true
python3 - "$TMP_ROOT/gateway-journal.raw" "$TMP_ROOT/journal-latency-safe.json" <<'PY_JOURNAL_LATENCY'
import json,re,statistics,sys
from pathlib import Path
text=Path(sys.argv[1]).read_text(encoding='utf-8',errors='replace')
lines=text.splitlines()
agent_end=0; model_end=0; tool_duration=0
agent_values=[]; model_values=[]; tool_values=[]
for line in lines:
    low=line.lower()
    nums=[]
    for m in re.finditer(r'(?:durationMs|duration_ms|runtimeMs|elapsedMs)["\s:=]+([0-9]+(?:\.[0-9]+)?)',line,re.I):
        nums.append(float(m.group(1)))
    if 'agent_end' in low or 'agent end' in low:
        agent_end+=1; agent_values.extend(nums)
    if 'model_call_ended' in low or 'model call ended' in low:
        model_end+=1; model_values.extend(nums)
    if 'after_tool_call' in low or 'tool duration' in low or ('tool' in low and nums):
        tool_duration+=1; tool_values.extend(nums)
def stats(values):
    return {'sample_count':len(values),'median_ms':statistics.median(values) if values else None,'max_ms':max(values) if values else None}
payload={'agent_end_event_count':agent_end,'model_call_ended_event_count':model_end,'tool_duration_event_count':tool_duration,'agent_duration':stats(agent_values),'model_duration':stats(model_values),'tool_duration':stats(tool_values),'raw_line_count':len(lines),'raw_content_recorded':False,'secret_values_recorded':False}
Path(sys.argv[2]).write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
PY_JOURNAL_LATENCY
JOURNAL_AGENT_END_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["agent_end_event_count"])' "$TMP_ROOT/journal-latency-safe.json")"
JOURNAL_MODEL_CALL_ENDED_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["model_call_ended_event_count"])' "$TMP_ROOT/journal-latency-safe.json")"
JOURNAL_TOOL_DURATION_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tool_duration_event_count"])' "$TMP_ROOT/journal-latency-safe.json")"

: > "$TMP_ROOT/http-public.csv"
: > "$TMP_ROOT/http-direct.csv"
for i in 1 2 3 4 5; do
  curl -sS -k --max-time 15 -o /dev/null -w '%{http_code},%{time_connect},%{time_starttransfer},%{time_total}\n' "https://$DOMAIN/" >> "$TMP_ROOT/http-public.csv" 2>/dev/null || true
  curl -sS --max-time 15 -o /dev/null -w '%{http_code},%{time_connect},%{time_starttransfer},%{time_total}\n' "http://127.0.0.1:$OPENCLAW_PORT/" >> "$TMP_ROOT/http-direct.csv" 2>/dev/null || true
  sleep 1
done
python3 - "$TMP_ROOT/http-public.csv" "$TMP_ROOT/http-direct.csv" "$TMP_ROOT/http-latency-safe.json" <<'PY_HTTP_LATENCY'
import json,statistics,sys
from pathlib import Path
def parse(path):
    rows=[]
    for line in Path(path).read_text().splitlines():
        parts=line.split(',')
        if len(parts)!=4 or parts[0]!='200': continue
        try: rows.append({'connect_ms':float(parts[1])*1000,'ttfb_ms':float(parts[2])*1000,'total_ms':float(parts[3])*1000})
        except Exception: pass
    def median(key): return statistics.median([x[key] for x in rows]) if rows else None
    return {'sample_count':len(rows),'median_connect_ms':median('connect_ms'),'median_ttfb_ms':median('ttfb_ms'),'median_total_ms':median('total_ms')}
payload={'public':parse(sys.argv[1]),'direct':parse(sys.argv[2]),'scope':'HTTP root transport only; not model TTFT or total assistant response latency.','secret_values_recorded':False}
Path(sys.argv[3]).write_text(json.dumps(payload,indent=2)+'\n')
PY_HTTP_LATENCY
PUBLIC_HTTP_SAMPLE_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["public"]["sample_count"])' "$TMP_ROOT/http-latency-safe.json")"
PUBLIC_HTTP_MEDIAN_TTFB_MS="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["public"]["median_ttfb_ms"]; print("unknown" if v is None else round(v,1))' "$TMP_ROOT/http-latency-safe.json")"
PUBLIC_HTTP_MEDIAN_TOTAL_MS="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["public"]["median_total_ms"]; print("unknown" if v is None else round(v,1))' "$TMP_ROOT/http-latency-safe.json")"
DIRECT_HTTP_MEDIAN_TTFB_MS="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["direct"]["median_ttfb_ms"]; print("unknown" if v is None else round(v,1))' "$TMP_ROOT/http-latency-safe.json")"
DIRECT_HTTP_MEDIAN_TOTAL_MS="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["direct"]["median_total_ms"]; print("unknown" if v is None else round(v,1))' "$TMP_ROOT/http-latency-safe.json")"

if [ "$TOOL_PLUGIN_SDK_SUPPORTED" = "YES" ] && [ "$PLUGIN_ENTRY_SDK_SUPPORTED" = "YES" ] && [ "$AGENT_END_HOOK_SUPPORTED" = "YES" ] && [ "$MODEL_CALL_HOOKS_SUPPORTED" = "YES" ] && [ "$AFTER_TOOL_CALL_HOOK_SUPPORTED" = "YES" ]; then
  LATENCY_OBSERVABILITY_PATH="PLUGIN_HOOKS_AGENT_END_MODEL_CALL_ENDED_AFTER_TOOL_CALL"
  RECOMMENDED_PLUGIN_SHAPE="MIXED_NATIVE_PLUGIN_DEFINE_PLUGIN_ENTRY_REGISTER_TOOLS_AND_HOOKS"
elif [ "$TOOL_PLUGIN_SDK_SUPPORTED" = "YES" ]; then
  LATENCY_OBSERVABILITY_PATH="EXTERNAL_METRICS_REQUIRED"
  RECOMMENDED_PLUGIN_SHAPE="TOOL_ONLY_PLUGIN_PLUS_SEPARATE_TELEMETRY"
else
  LATENCY_OBSERVABILITY_PATH="UNSUPPORTED_PENDING_REVIEW"
  RECOMMENDED_PLUGIN_SHAPE="DO_NOT_IMPLEMENT_UNTIL_COMPATIBILITY_REVIEW"
fi

OPENCLAW_CONFIG_HASH_AFTER="$(sha256sum "$OPENCLAW_CONFIG" | awk '{print $1}')"
OPENCLAW_SERVICE_MAINPID_AFTER="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"
PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
if [ "$OPENCLAW_CONFIG_HASH_BEFORE" = "$OPENCLAW_CONFIG_HASH_AFTER" ] && [ "$OPENCLAW_SERVICE_MAINPID_BEFORE" = "$OPENCLAW_SERVICE_MAINPID_AFTER" ]; then CONFIG_OR_SERVICE_CHANGED="NO"; else fail_now "openclaw_config_or_service_changed_during_discovery" "INSPECT_UNEXPECTED_RUNTIME_MUTATION"; fi
if [ "$PRODUCT_HEAD_AFTER" = "$PRODUCT_HEAD_BEFORE" ] && [ "$PRODUCT_REMOTE_AFTER" = "$PRODUCT_REMOTE_BEFORE" ] && [ "$PRODUCT_STATUS_AFTER" = "$PRODUCT_STATUS_BEFORE" ] && [ "$PRODUCT_TREE_AFTER" = "$PRODUCT_TREE_BEFORE" ]; then PRODUCT_BASELINE_PRESERVED="YES"; else fail_now "product_baseline_changed_during_discovery" "RESTORE_COMPLETED_PRODUCT_BASELINE"; fi

DISCOVERY_COMPLETE="YES"
RESULT="DIAGNOSED"
NEXT_ACTION="DESIGN_MINIMAL_ORIS_NATIVE_PLUGIN_WITH_OPTIONAL_TYPED_TOOLS_POLICY_HOOKS_AND_LATENCY_TELEMETRY"

export TASK_ID PREVIOUS_TASK_ID STAMP RESULT FAILURE_CODE DISCOVERY_COMPLETE OPENCLAW_VERSION NODE_VERSION OPENCLAW_SERVICE_STATE OPENCLAW_DIRECT_STATUS PUBLIC_ROOT_STATUS PUBLIC_ROOT_MATCHES_DIRECT PLUGIN_CLI_SUPPORTED PLUGIN_LIST_RC PLUGIN_INSPECT_COLD_RC PLUGIN_INSPECT_RUNTIME_RC PLUGIN_DOCTOR_RC GATEWAY_DEEP_STATUS_RC PLUGIN_TOTAL_COUNT PLUGIN_ENABLED_COUNT PLUGIN_ERROR_COUNT EXISTING_ORIS_PLUGIN_COUNT REGISTERED_TOOL_COUNT REGISTERED_HOOK_COUNT TOOL_PLUGIN_SDK_SUPPORTED PLUGIN_ENTRY_SDK_SUPPORTED AUTHORING_CLI_SUPPORTED AGENT_END_HOOK_SUPPORTED MODEL_CALL_HOOKS_SUPPORTED AFTER_TOOL_CALL_HOOK_SUPPORTED PLUGIN_POLICY_MODE TOOLS_POLICY_MODE HARNESS_SERVICE_COUNT HARNESS_ACTIVE_COUNT ORIS_CANDIDATE_ROUTE_COUNT ORIS_INTEGRATION_FILE_COUNT SESSION_RUNTIME_SAMPLE_COUNT JOURNAL_AGENT_END_COUNT JOURNAL_MODEL_CALL_ENDED_COUNT JOURNAL_TOOL_DURATION_COUNT PUBLIC_HTTP_SAMPLE_COUNT PUBLIC_HTTP_MEDIAN_TTFB_MS PUBLIC_HTTP_MEDIAN_TOTAL_MS DIRECT_HTTP_MEDIAN_TTFB_MS DIRECT_HTTP_MEDIAN_TOTAL_MS LATENCY_OBSERVABILITY_PATH RECOMMENDED_PLUGIN_SHAPE ACTIVE_QUEUE_COUNT INTAKE_LOOPBACK_ONLY PRODUCT_BASELINE_PRESERVED CONFIG_OR_SERVICE_CHANGED PRODUCT_TASK_SUBMITTED NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$TMP_ROOT/plugin-summary.json" "$TMP_ROOT/config-safe.json" "$TMP_ROOT/package-safe.json" "$TMP_ROOT/services-safe.json" "$TMP_ROOT/oris-integration-safe.json" "$TMP_ROOT/session-latency-safe.json" "$TMP_ROOT/journal-latency-safe.json" "$TMP_ROOT/http-latency-safe.json" "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path
files=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:9]]
plugin,config,package,services,oris,session,journal,http=files
payload={
 'task_id':os.environ['TASK_ID'],
 'previous_task_id':os.environ['PREVIOUS_TASK_ID'],
 'checked_at':os.environ['STAMP'],
 'result':os.environ['RESULT'],
 'failure_code':os.environ.get('FAILURE_CODE') or None,
 'openclaw':{
   'version':os.environ['OPENCLAW_VERSION'],
   'node_version':os.environ['NODE_VERSION'],
   'service_state':os.environ['OPENCLAW_SERVICE_STATE'],
   'direct_status':os.environ['OPENCLAW_DIRECT_STATUS'],
   'public_status':os.environ['PUBLIC_ROOT_STATUS'],
   'public_matches_direct':os.environ['PUBLIC_ROOT_MATCHES_DIRECT']=='YES',
   'plugin_cli_supported':os.environ['PLUGIN_CLI_SUPPORTED']=='YES',
   'plugin_list_rc':int(os.environ['PLUGIN_LIST_RC']),
   'plugin_inspect_cold_rc':int(os.environ['PLUGIN_INSPECT_COLD_RC']),
   'plugin_inspect_runtime_rc':int(os.environ['PLUGIN_INSPECT_RUNTIME_RC']),
   'plugin_doctor_rc':int(os.environ['PLUGIN_DOCTOR_RC']),
   'gateway_deep_status_rc':int(os.environ['GATEWAY_DEEP_STATUS_RC']),
 },
 'sdk':{
   'tool_plugin_supported':os.environ['TOOL_PLUGIN_SDK_SUPPORTED']=='YES',
   'plugin_entry_supported':os.environ['PLUGIN_ENTRY_SDK_SUPPORTED']=='YES',
   'authoring_cli_supported':os.environ['AUTHORING_CLI_SUPPORTED']=='YES',
   'agent_end_hook_supported':os.environ['AGENT_END_HOOK_SUPPORTED']=='YES',
   'model_call_hooks_supported':os.environ['MODEL_CALL_HOOKS_SUPPORTED']=='YES',
   'after_tool_call_hook_supported':os.environ['AFTER_TOOL_CALL_HOOK_SUPPORTED']=='YES',
   'package':package,
 },
 'plugins':plugin,
 'policy':config,
 'services':services,
 'oris_integration':oris,
 'latency':{
   'session_metadata':session,
   'recent_gateway_journal':journal,
   'http_transport':http,
   'observability_path':os.environ['LATENCY_OBSERVABILITY_PATH'],
   'recommended_plugin_shape':os.environ['RECOMMENDED_PLUGIN_SHAPE'],
   'model_latency_measured':False,
   'ttft_measured':False,
 },
 'safety':{
   'active_queue_count':int(os.environ['ACTIVE_QUEUE_COUNT']),
   'intake_loopback_only':os.environ['INTAKE_LOOPBACK_ONLY']=='YES',
   'product_baseline_preserved':os.environ['PRODUCT_BASELINE_PRESERVED']=='YES',
   'config_or_service_changed':os.environ['CONFIG_OR_SERVICE_CHANGED']=='YES',
   'product_task_submitted':False,
   'product_repository_mutated':False,
   'openclaw_reinstalled_or_upgraded':False,
   'secret_values_recorded':False,
 },
 'next_action':os.environ['NEXT_ACTION'],
 'evidence':{'log_path':os.environ['EVIDENCE_LOG_REL'],'json_path':os.environ['EVIDENCE_JSON_REL'],'self_commit_sha_omitted_to_prevent_post_commit_log_drift':True},
}
Path(sys.argv[9]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_RESULT

{
  echo "OPENCLAW_VERSION=$OPENCLAW_VERSION"
  echo "NODE_VERSION=$NODE_VERSION"
  echo "PLUGIN_TOTAL_COUNT=$PLUGIN_TOTAL_COUNT"
  echo "PLUGIN_ENABLED_COUNT=$PLUGIN_ENABLED_COUNT"
  echo "PLUGIN_ERROR_COUNT=$PLUGIN_ERROR_COUNT"
  echo "EXISTING_ORIS_PLUGIN_COUNT=$EXISTING_ORIS_PLUGIN_COUNT"
  echo "REGISTERED_TOOL_COUNT=$REGISTERED_TOOL_COUNT"
  echo "REGISTERED_HOOK_COUNT=$REGISTERED_HOOK_COUNT"
  echo "TOOL_PLUGIN_SDK_SUPPORTED=$TOOL_PLUGIN_SDK_SUPPORTED"
  echo "PLUGIN_ENTRY_SDK_SUPPORTED=$PLUGIN_ENTRY_SDK_SUPPORTED"
  echo "AUTHORING_CLI_SUPPORTED=$AUTHORING_CLI_SUPPORTED"
  echo "AGENT_END_HOOK_SUPPORTED=$AGENT_END_HOOK_SUPPORTED"
  echo "MODEL_CALL_HOOKS_SUPPORTED=$MODEL_CALL_HOOKS_SUPPORTED"
  echo "AFTER_TOOL_CALL_HOOK_SUPPORTED=$AFTER_TOOL_CALL_HOOK_SUPPORTED"
  echo "LATENCY_OBSERVABILITY_PATH=$LATENCY_OBSERVABILITY_PATH"
  echo "RECOMMENDED_PLUGIN_SHAPE=$RECOMMENDED_PLUGIN_SHAPE"
  echo "RAW_PLUGIN_OR_JOURNAL_CONTENT_COMMITTED=NO"
  echo "SECRET_VALUES_RECORDED=NO"
} >> "$RUN_LOG"

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY_SECRET_SCAN'
import re,sys
from pathlib import Path
patterns=[
 re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
 re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),
 re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),
 re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
 re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
 re.compile(r'(?i)(password|authorization|credential|gateway[_ -]?token|api[_ -]?key|secret)(\s*[=:]\s*|\s+)(?!<redacted>|true\b|false\b|yes\b|no\b|null\b|unchanged\b|values\b|recorded\b)[A-Za-z0-9._~+/-]{16,}'),
]
for filename in sys.argv[1:]:
    text=Path(filename).read_text(encoding='utf-8',errors='replace')
    if any(p.search(text) for p in patterns): raise SystemExit(1)
PY_SECRET_SCAN
if [ "$?" -eq 0 ]; then SECRET_SCAN="PASS"; else fail_now "discovery_evidence_secret_scan_failed" "REPAIR_DISCOVERY_REDACTION"; fi

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL" || fail_now "evidence_directory_create_failed" "CHECK_EVIDENCE_WORKTREE_PERMISSIONS"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_NORMALIZE'
import json,sys
from pathlib import Path
sl,dl,sj,dj=map(Path,sys.argv[1:])
dl.write_text('\n'.join(line.rstrip(' \t\r') for line in sl.read_text(encoding='utf-8',errors='replace').splitlines())+'\n',encoding='utf-8')
dj.write_text(json.dumps(json.loads(sj.read_text(encoding='utf-8')),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_NORMALIZE
[ "$?" -eq 0 ] || fail_now "evidence_normalization_failed" "INSPECT_DISCOVERY_EVIDENCE"
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record OpenClaw tool plugin discovery $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then EVIDENCE_REMOTE_VERIFIED="YES"; else RESULT="FAILED"; FAILURE_CODE="evidence_remote_sha_mismatch"; NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"; fi

summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
