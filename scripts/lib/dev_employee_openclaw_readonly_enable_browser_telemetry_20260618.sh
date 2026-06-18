TELEMETRY_PATH="$HOME/.local/state/oris/openclaw-plugin/latency.jsonl"
BROWSER_PHASE_START="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
BROWSER_WAIT_SECONDS="${ORIS_BROWSER_ACCEPTANCE_TIMEOUT_SECONDS:-900}"
case "$BROWSER_WAIT_SECONDS" in *[!0-9]*|'') BROWSER_WAIT_SECONDS=900 ;; esac
[ "$BROWSER_WAIT_SECONDS" -ge 60 ] || BROWSER_WAIT_SECONDS=60
[ "$BROWSER_WAIT_SECONDS" -le 1800 ] || BROWSER_WAIT_SECONDS=1800

printf '%s\n' "===== BROWSER ACCEPTANCE REQUIRED ====="
printf '%s\n' "Open https://control.orisfy.com in the already-authorized OpenClaw browser session."
printf '%s\n' "Send these three natural-language messages one at a time and wait for each answer:"
printf '%s\n' "1) 请实时查看当前 ORIS 开发员工队列状态，并告诉我现在是否有任务正在运行。"
printf '%s\n' "2) 请实时查看 ORIS 最近一个任务的状态，并概括它当前处于哪个阶段。"
printf '%s\n' "3) 请实时查看任务 commercial-openclaw-readonly-tool-enable-20260618 的状态，并说明下一步是什么。"
printf '%s\n' "The script will detect the three typed read-only tool calls from privacy-safe telemetry."
printf '%s\n' "It will automatically restore tools-denied state if acceptance does not complete before timeout."
printf '%s\n' "===== END BROWSER INSTRUCTIONS ====="

browser_telemetry_snapshot() {
  python3 - "$TELEMETRY_PATH" "$BROWSER_PHASE_START" "$TMP_ROOT/browser-telemetry-safe.json" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY'
import json,re,statistics,sys
from pathlib import Path
path=Path(sys.argv[1]); start=sys.argv[2]; out=Path(sys.argv[3]); expected=set(sys.argv[4:7])
allowed_keys={'timestamp','event','durationMs','outcome','success','error','provider','model','toolName','runHash','callHash','sessionHash'}
allowed_events={'model_call_ended','after_tool_call','agent_end'}
forbidden=re.compile(r'(prompt|message|content|text|argument|result|header|token|password|secret|credential|cookie|authorization|api.?key)',re.I)
secret_patterns=[re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),re.compile(r'Bearer\s+[A-Za-z0-9._~+/=-]{12,}',re.I),re.compile(r'/(?:home|root|etc|var|opt|srv|tmp)/[^\s"}]+')]
records=[]; schema_ok=True; content_safe=True
def mode_owner_ok(candidate, expected_mode):
 if not candidate.exists(): return True
 st=candidate.stat(); return st.st_uid==Path.home().stat().st_uid and (st.st_mode & 0o777)==expected_mode
parent_ok=(not path.parent.exists()) or mode_owner_ok(path.parent,0o700)
file_permissions_ok=mode_owner_ok(path,0o600) and mode_owner_ok(Path(str(path)+'.1'),0o600)
for candidate in (Path(str(path)+'.1'),path):
 if not candidate.exists(): continue
 raw=candidate.read_text(encoding='utf-8',errors='replace')
 if any(p.search(raw) for p in secret_patterns): content_safe=False
 for line in raw.splitlines():
  if not line.strip(): continue
  try: item=json.loads(line)
  except Exception: schema_ok=False; continue
  if not isinstance(item,dict): schema_ok=False; continue
  if str(item.get('timestamp') or '') < start: continue
  keys=set(item)
  if not keys.issubset(allowed_keys) or any(forbidden.search(k) for k in keys): schema_ok=False
  if item.get('event') not in allowed_events: schema_ok=False
  for k in ('runHash','callHash','sessionHash'):
   if k in item and not re.fullmatch(r'[0-9a-f]{64}',str(item[k])): schema_ok=False
  if item.get('error') is True or item.get('success') is False: schema_ok=False
  records.append(item)
seen={x.get('toolName') for x in records if x.get('event')=='after_tool_call'}
counts={e:sum(1 for x in records if x.get('event')==e) for e in allowed_events}
def durations(event,tool=None):
 vals=[]
 for x in records:
  if x.get('event')!=event: continue
  if tool is not None and x.get('toolName')!=tool: continue
  v=x.get('durationMs')
  if isinstance(v,(int,float)) and v>=0: vals.append(float(v))
 return vals
def stats(vals):
 if not vals: return {'available':False,'count':0}
 return {'available':True,'count':len(vals),'min_ms':round(min(vals),3),'p50_ms':round(statistics.median(vals),3),'max_ms':round(max(vals),3)}
metrics={
 'ttft':{'available':False,'reason':'current approved typed hooks do not expose first-token timestamp'},
 'model_duration':stats(durations('model_call_ended')),
 'total_agent_duration':stats(durations('agent_end')),
 'tool_duration':{tool:stats(durations('after_tool_call',tool)) for tool in sorted(expected)},
}
accepted=expected.issubset(seen) and counts['model_call_ended']>=3 and counts['agent_end']>=3 and schema_ok and content_safe and parent_ok and file_permissions_ok
payload={'accepted':accepted,'expected_tools_seen':sorted(expected.intersection(seen)),'event_counts':counts,'schema_ok':schema_ok,'content_safe':content_safe,'parent_permissions_ok':parent_ok,'file_permissions_ok':file_permissions_ok,'metrics':metrics,'records_after_start':len(records),'secret_values_recorded':False,'conversation_content_recorded':False}
out.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n')
PY
}

BROWSER_ACCEPTED="NO"
for elapsed in $(seq 0 5 "$BROWSER_WAIT_SECONDS"); do
  browser_telemetry_snapshot >/dev/null 2>&1 || true
  if [ -f "$TMP_ROOT/browser-telemetry-safe.json" ]; then
    BROWSER_ACCEPTED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1])).get("accepted") else "NO")' "$TMP_ROOT/browser-telemetry-safe.json" 2>/dev/null || echo NO)"
  fi
  if [ "$BROWSER_ACCEPTED" = "YES" ]; then break; fi
  sleep 5
done
[ "$BROWSER_ACCEPTED" = "YES" ] || fatal "browser_natural_language_acceptance_timeout_or_failed" "RERUN_ENABLEMENT_AND_COMPLETE_THREE_BROWSER_PROMPTS"
BROWSER_ACCEPTANCE_PASS="YES"
TELEMETRY_PRIVACY_PASS="YES"
record_check "browser_natural_language_acceptance" "PASS" "queue_latest_task_tools_observed_in_native_agent_runs"
record_check "telemetry_privacy_and_schema" "PASS" "three_hooks_schema_safe_no_content_or_secret_fields"
