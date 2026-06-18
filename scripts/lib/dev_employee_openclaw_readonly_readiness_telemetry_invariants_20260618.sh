# Telemetry path, permissions, rotation contract, schema and content safety.
python3 - "$TMP_ROOT/config-safe.json" "$ORIS_REPO/$PLUGIN_REL/src/index.ts" "$TMP_ROOT/telemetry-safe.json" <<'PY_TELEMETRY'
import json, os, re, sys
from pathlib import Path
cfg=json.load(open(sys.argv[1])); source=Path(sys.argv[2]); out=Path(sys.argv[3])
raw_path=cfg['telemetry_path']
if raw_path=='~': target=Path.home()
elif raw_path.startswith('~/'): target=Path.home()/raw_path[2:]
else: target=Path(raw_path).expanduser()
target=target.resolve()
rotated=Path(str(target)+'.1')
allowed_keys={'timestamp','event','durationMs','outcome','success','error','provider','model','toolName','runHash','callHash','sessionHash'}
allowed_events={'model_call_ended','after_tool_call','agent_end'}
forbidden_key=re.compile(r'(prompt|message|content|text|argument|result|header|token|password|secret|credential|cookie|authorization|api.?key)',re.I)
secret_patterns=[
 re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
 re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),
 re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),
 re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
 re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
 re.compile(r'Bearer\s+[A-Za-z0-9._~+/=-]{12,}',re.I),
 re.compile(r'/(?:home|root|etc|var|opt|srv|tmp)/[^\s"}]+'),
]
def meta(path, expect_mode):
 if not path.exists(): return {'exists':False,'owner_ok':None,'mode_ok':None,'size':0}
 st=path.stat(); return {'exists':True,'owner_ok':st.st_uid==os.getuid(),'mode_ok':(st.st_mode & 0o777)==expect_mode,'size':st.st_size}
def scan(path):
 result={'records':0,'json_ok':True,'schema_ok':True,'content_safe':True,'events':[]}
 if not path.exists(): return result
 events=set()
 try:
  raw=path.read_text(encoding='utf-8',errors='replace')
  if any(p.search(raw) for p in secret_patterns): result['content_safe']=False
  for line in raw.splitlines():
   if not line.strip(): continue
   result['records']+=1
   try: item=json.loads(line)
   except Exception: result['json_ok']=False; continue
   if not isinstance(item,dict): result['schema_ok']=False; continue
   keys=set(item)
   if not keys.issubset(allowed_keys) or any(forbidden_key.search(k) for k in keys): result['schema_ok']=False
   event=item.get('event')
   if event not in allowed_events: result['schema_ok']=False
   else: events.add(event)
   for key in ('runHash','callHash','sessionHash'):
    if key in item and not re.fullmatch(r'[0-9a-f]{64}',str(item[key])): result['schema_ok']=False
   if 'durationMs' in item and (not isinstance(item['durationMs'],(int,float)) or item['durationMs']<0): result['schema_ok']=False
   for key in ('provider','model','toolName','outcome'):
    if key in item and (not isinstance(item[key],str) or len(item[key])>160): result['schema_ok']=False
  result['events']=sorted(events)
 except Exception:
  result['json_ok']=False; result['content_safe']=False
 return result
source_text=source.read_text(encoding='utf-8',errors='replace') if source.is_file() else ''
rotation_contract=all(x in source_text for x in ('telemetryMaxBytes','rename(target, rotated)',"`${target}.1`",'mode: 0o600'))
within_home = target==Path.home() or Path.home() in target.parents
parent=target.parent
payload={
 'telemetry_enabled':cfg['telemetry_enabled'],
 'path_within_home':within_home,
 'path_suffix_ok':str(target).endswith('/.local/state/oris/openclaw-plugin/latency.jsonl'),
 'max_bytes':cfg['telemetry_max_bytes'],
 'max_bytes_valid':isinstance(cfg['telemetry_max_bytes'],int) and 65536 <= cfg['telemetry_max_bytes'] <= 52428800,
 'parent':meta(parent,0o700),
 'current':meta(target,0o600),
 'rotated':meta(rotated,0o600),
 'current_scan':scan(target),
 'rotated_scan':scan(rotated),
 'rotation_contract_static':rotation_contract,
 'source_exists':source.is_file(),
 'secret_values_recorded':False,
}
out.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n',encoding='utf-8')
PY_TELEMETRY
if [ "$?" -ne 0 ]; then
  record_check "telemetry_safety" "FAIL" "telemetry_safe_parser_failed"
else
  TELEMETRY_CORE_OK="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); files=[d["current"],d["rotated"]]; perms=all((not f["exists"]) or (f["owner_ok"] and f["mode_ok"]) for f in files); parent=(not d["parent"]["exists"]) or (d["parent"]["owner_ok"] and d["parent"]["mode_ok"]); scans=[d["current_scan"],d["rotated_scan"]]; safe=all(x["json_ok"] and x["schema_ok"] and x["content_safe"] for x in scans); print("YES" if d["telemetry_enabled"] and d["path_within_home"] and d["max_bytes_valid"] and d["rotation_contract_static"] and perms and parent and safe else "NO")' "$TMP_ROOT/telemetry-safe.json")"
  TELEMETRY_RECORDS="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["current_scan"]["records"]+d["rotated_scan"]["records"])' "$TMP_ROOT/telemetry-safe.json")"
  if [ "$TELEMETRY_CORE_OK" = "YES" ]; then
    if [ "$TELEMETRY_RECORDS" -gt 0 ]; then record_check "telemetry_safety" "PASS" "private_rotated_schema_safe_existing_records_$TELEMETRY_RECORDS"; else record_check "telemetry_safety" "PASS" "private_rotation_schema_contract_no_samples_yet"; fi
  else
    record_check "telemetry_safety" "FAIL" "telemetry_path_permission_rotation_schema_or_content_failure"
  fi
fi

# Queue and product baseline checks.
[ "$ACTIVE_QUEUE_COUNT_BEFORE" = "0" ] && record_check "active_queue_count" "PASS" "zero_active_tasks" || record_check "active_queue_count" "FAIL" "active_queue_count_$ACTIVE_QUEUE_COUNT_BEFORE"
if [ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] && [ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] && [ "$PRODUCT_STATUS_SHA_BEFORE" = "$(printf '' | sha256sum | awk '{print $1}')" ]; then
  record_check "product_repository_baseline" "PASS" "head_remote_main_exact_and_clean"
else
  record_check "product_repository_baseline" "FAIL" "product_head_remote_or_worktree_mismatch"
fi

# Before/after invariants: config, PID, queue and product repository must not change.
OPENCLAW_CONFIG_SHA_AFTER="$(sha256sum "$OPENCLAW_CONFIG" 2>/dev/null | awk '{print $1}')"
OPENCLAW_PID_AFTER="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"
GATEWAY_STATE_AFTER="$(systemctl --user is-active "$OPENCLAW_SERVICE" 2>/dev/null || true)"
QUEUE_FINGERPRINT_AFTER="$(queue_fingerprint)"
ACTIVE_QUEUE_COUNT_AFTER="$(active_queue_count)"
PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER_FILE="$TMP_ROOT/product-status-after.bin"
git -C "$PRODUCT_REPO" status --porcelain=v1 -z --untracked-files=all > "$PRODUCT_STATUS_AFTER_FILE" 2>/dev/null || fatal "product_status_recapture_failed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_STATUS_SHA_AFTER="$(sha256sum "$PRODUCT_STATUS_AFTER_FILE" | awk '{print $1}')"
PRODUCT_TREE_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
ORIS_HEAD_AFTER="$(git -C "$ORIS_REPO" rev-parse HEAD 2>/dev/null || true)"
ORIS_STATUS_AFTER_FILE="$TMP_ROOT/oris-status-after.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_AFTER_FILE" 2>/dev/null || fatal "oris_status_recapture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_SHA_AFTER="$(sha256sum "$ORIS_STATUS_AFTER_FILE" | awk '{print $1}')"

if [ "$OPENCLAW_CONFIG_SHA_BEFORE" = "$OPENCLAW_CONFIG_SHA_AFTER" ]; then record_check "openclaw_config_unchanged" "PASS" "sha256_unchanged"; else record_check "openclaw_config_unchanged" "FAIL" "config_hash_changed"; fi
if [ "$OPENCLAW_PID_BEFORE" = "$OPENCLAW_PID_AFTER" ] && [ "$GATEWAY_STATE_AFTER" = "active" ]; then record_check "gateway_pid_unchanged" "PASS" "same_main_pid_no_restart"; else record_check "gateway_pid_unchanged" "FAIL" "pid_or_state_changed"; fi
if [ "$QUEUE_FINGERPRINT_BEFORE" = "$QUEUE_FINGERPRINT_AFTER" ] && [ "$ACTIVE_QUEUE_COUNT_BEFORE" = "$ACTIVE_QUEUE_COUNT_AFTER" ]; then record_check "queue_unchanged" "PASS" "fingerprint_and_active_count_unchanged"; else record_check "queue_unchanged" "FAIL" "queue_fingerprint_or_count_changed"; fi
if [ "$PRODUCT_HEAD_BEFORE" = "$PRODUCT_HEAD_AFTER" ] && [ "$PRODUCT_REMOTE_BEFORE" = "$PRODUCT_REMOTE_AFTER" ] && [ "$PRODUCT_STATUS_SHA_BEFORE" = "$PRODUCT_STATUS_SHA_AFTER" ] && [ "$PRODUCT_TREE_BEFORE" = "$PRODUCT_TREE_AFTER" ]; then record_check "product_repository_unchanged" "PASS" "head_remote_status_tree_unchanged"; else record_check "product_repository_unchanged" "FAIL" "product_repository_changed"; fi
if [ "$ORIS_HEAD_BEFORE" = "$ORIS_HEAD_AFTER" ] && [ "$ORIS_STATUS_SHA_BEFORE" = "$ORIS_STATUS_SHA_AFTER" ]; then record_check "oris_primary_worktree_unchanged" "PASS" "head_and_status_unchanged_before_evidence_commit"; else record_check "oris_primary_worktree_unchanged" "FAIL" "primary_worktree_changed"; fi

# Determine readiness result before evidence commit.
if [ "$CHECK_FAIL" -eq 0 ] && [ "$CHECK_REVIEW" -eq 0 ]; then
  RESULT="READY"
  NEXT_ACTION="CREATE_REVERSIBLE_READ_ONLY_ENABLEMENT_SCRIPT_FROM_EVIDENCE"
elif [ "$CHECK_FAIL" -eq 0 ]; then
  RESULT="REVIEW"
  NEXT_ACTION="REVIEW_POLICY_OR_ROUTE_AMBIGUITY_BEFORE_ENABLEMENT"
else
  RESULT="FAILED"
  FAILURE_CODE="readiness_gate_failed"
  NEXT_ACTION="FIX_READINESS_FAILURE_WITHOUT_ENABLING_TOOLS"
fi

