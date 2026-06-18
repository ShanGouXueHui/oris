apply_policy_mode() {
  local mode="$1"
  cp "$CONFIG_BACKUP_FILE" "$OPENCLAW_CONFIG" >/dev/null 2>&1 || return 1
  chmod 600 "$OPENCLAW_CONFIG" >/dev/null 2>&1 || return 1
  python3 - "$OPENCLAW_CONFIG" "$mode" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY'
import json,os,sys
from pathlib import Path
path=Path(sys.argv[1]); mode=sys.argv[2]; approved=sys.argv[3:6]
data=json.loads(path.read_text(encoding='utf-8')); tools=data.get('tools')
if not isinstance(tools,dict) or tools.get('profile')!='coding': raise SystemExit(2)
deny=tools.get('deny')
if not isinstance(deny,list) or set(deny)!=set(approved) or len(deny)!=3: raise SystemExit(3)
tools['deny']=[x for x in deny if x not in approved]
if mode=='exact-approved-tools':
 tools['allow']=approved
elif mode=='materialized-coding-plus-approved':
 tools['allow']=['group:fs','group:runtime','group:web','group:sessions','group:memory','cron','image','image_generate','skill_workshop','video_generate',*approved]
else: raise SystemExit(4)
tmp=path.with_name(path.name+'.readonly-enable.tmp')
tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.chmod(tmp,0o600)
json.loads(tmp.read_text(encoding='utf-8')); os.replace(tmp,path); os.chmod(path,0o600)
PY
  [ "$?" -eq 0 ] || return 1
  MUTATION_STARTED="YES"
  restart_gateway_and_wait || return 1
  verify_public_and_restricted_routes || return 1
  return 0
}

validate_config_scope() {
  local mode="$1"
  python3 - "$CONFIG_BACKUP_FILE" "$OPENCLAW_CONFIG" "$mode" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY'
import json,sys
from pathlib import Path
before=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')); after=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
mode=sys.argv[3]; approved=sys.argv[4:7]
def stripped(d):
 x=json.loads(json.dumps(d)); tools=x.get('tools') if isinstance(x.get('tools'),dict) else {}
 tools.pop('allow',None); tools.pop('deny',None); return x
if stripped(before)!=stripped(after): raise SystemExit(2)
tools=after.get('tools') if isinstance(after.get('tools'),dict) else {}
if tools.get('profile')!='coding' or tools.get('deny')!=[]: raise SystemExit(3)
expected=approved if mode=='exact-approved-tools' else ['group:fs','group:runtime','group:web','group:sessions','group:memory','cron','image','image_generate','skill_workshop','video_generate',*approved]
if tools.get('allow')!=expected: raise SystemExit(4)
PY
}

inspect_runtime_safe() {
  openclaw plugins list --json > "$TMP_ROOT/plugins-list.json" 2>/dev/null || return 1
  openclaw plugins inspect "$PLUGIN_ID" --runtime --json > "$TMP_ROOT/plugin-runtime.json" 2>/dev/null || return 1
  python3 - "$TMP_ROOT/plugins-list.json" "$TMP_ROOT/plugin-runtime.json" "$PLUGIN_ID" "$TOOL_1" "$TOOL_2" "$TOOL_3" "$HOOK_1" "$HOOK_2" "$HOOK_3" <<'PY'
import json,sys
from pathlib import Path
listing=json.loads(Path(sys.argv[1]).read_text()); runtime=json.loads(Path(sys.argv[2]).read_text()); plugin=sys.argv[3]
expected_tools=set(sys.argv[4:7]); expected_hooks=set(sys.argv[7:10]); found=False; enabled=False; errors=0
for item in listing.get('plugins',[]):
 if isinstance(item,dict) and str(item.get('id') or item.get('name') or '')==plugin:
  found=True; enabled=item.get('enabled') is True
  if item.get('status')=='error' or item.get('error'): errors+=1
tools=set(); hooks=set()
def add(v,t):
 if isinstance(v,list):
  for x in v:
   if isinstance(x,str): t.add(x)
   elif isinstance(x,dict):
    n=x.get('name') or x.get('id') or x.get('toolName') or x.get('hookName')
    if isinstance(n,str): t.add(n)
 elif isinstance(v,dict):
  for k in v:
   if isinstance(k,str): t.add(k)
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
write={x for x in tools if any(w in x.lower() for w in ('submit','cancel','retry','create','enqueue','mutate','write','delete','update'))}
raise SystemExit(0 if found and enabled and errors==0 and tools==expected_tools and hooks==expected_hooks and not write else 1)
PY
}

direct_probe_mode() {
  local mode="$1" output="$TMP_ROOT/direct-$mode.json"
  python3 - "$OPENCLAW_CONFIG" "$output" "$TASK_ID" "$BASELINE_SAFE_TOOL" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY'
import json,time,urllib.request,urllib.error,sys
from pathlib import Path
cfg=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')); token=cfg['gateway']['auth']['token']; out=Path(sys.argv[2]); task=sys.argv[3]; baseline=sys.argv[4]; names=sys.argv[5:8]
url='http://127.0.0.1:18789/tools/invoke'
calls=[(baseline,{ }),(names[0],{}),(names[1],{'task_id':task}),(names[2],{})]
rows=[]
for tool,args in calls:
 req=urllib.request.Request(url,data=json.dumps({'tool':tool,'args':args,'sessionKey':'main'}).encode(),method='POST',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
 start=time.perf_counter(); status=0; ok=False; contract=False
 try:
  with urllib.request.urlopen(req,timeout=15) as resp:
   status=resp.status; payload=json.loads(resp.read(1000000)); ok=status==200 and payload.get('ok') is True
   if tool==baseline: contract=ok
   else:
    result=payload.get('result') if isinstance(payload,dict) else None
    details=result.get('details') if isinstance(result,dict) and isinstance(result.get('details'),dict) else {}
    content=result.get('content') if isinstance(result,dict) else None
    text=None
    if isinstance(content,list) and content and isinstance(content[0],dict): text=content[0].get('text')
    try: parsed=json.loads(text) if isinstance(text,str) else None
    except Exception: parsed=None
    contract=ok and details.get('source')=='oris-dev-employee' and details.get('readOnly') is True and details.get('sanitized') is True and parsed is not None
 except urllib.error.HTTPError as e: status=e.code
 except Exception: status=0
 rows.append({'tool':tool,'status':status,'ok':ok,'contract_ok':contract,'duration_ms':round((time.perf_counter()-start)*1000,3)})
approved=[x for x in rows if x['tool'] in names]; baseline_row=rows[0]
payload={'mode':sys.argv[2].split('/')[-1].replace('direct-','').replace('.json',''),'calls':rows,'baseline_preserved':baseline_row['contract_ok'],'approved_all_pass':len(approved)==3 and all(x['contract_ok'] for x in approved),'secret_values_recorded':False,'tool_results_recorded':False}
out.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n')
PY
  [ "$?" -eq 0 ] || return 1
  python3 - "$output" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); raise SystemExit(0 if d['approved_all_pass'] and d['baseline_preserved'] else 1)
PY
}

try_policy_mode() {
  local mode="$1"
  log "POLICY_ATTEMPT|$mode|started"
  apply_policy_mode "$mode" || return 1
  validate_config_scope "$mode" || return 1
  inspect_runtime_safe || return 1
  direct_probe_mode "$mode" || return 1
  SELECTED_POLICY_MODE="$mode"
  CONFIG_SCOPE_VALID="YES"
  DIRECT_TOOL_CALLS_PASS="YES"
  WRITE_TOOLS_ABSENT="YES"
  log "POLICY_ATTEMPT|$mode|passed"
  return 0
}

if try_policy_mode "exact-approved-tools"; then
  record_check "controlled_policy_enablement" "PASS" "exact_three_tool_allow_preserved_coding_baseline"
else
  log "POLICY_ATTEMPT|exact-approved-tools|failed_restoring_denied"
  restore_tools_denied || fatal "first_policy_attempt_rollback_failed" "MANUALLY_RESTORE_TOOLS_DENIED_BACKUP"
  if try_policy_mode "materialized-coding-plus-approved"; then
    record_check "controlled_policy_enablement" "PASS" "materialized_existing_coding_profile_plus_exact_three_tools"
  else
    fatal "both_policy_enablement_modes_failed" "INSPECT_EFFECTIVE_OPENCLAW_TOOL_POLICY"
  fi
fi
record_check "direct_readonly_tool_calls" "PASS" "queue_task_latest_and_baseline_tool_passed_gateway_invoke"

QUEUE_AFTER_DIRECT="$(queue_fingerprint)"
ACTIVE_AFTER_DIRECT="$(active_queue_count)"
[ "$QUEUE_FINGERPRINT_BEFORE" = "$QUEUE_AFTER_DIRECT" ] && [ "$ACTIVE_AFTER_DIRECT" = "0" ] || fatal "queue_changed_during_direct_tool_calls" "RESTORE_TOOLS_DENIED_AND_INSPECT_QUEUE"
record_check "queue_after_direct_calls" "PASS" "fingerprint_unchanged_zero_active"
