#!/usr/bin/env bash

TASK_ID="commercial-openclaw-readonly-tool-enable-20260618"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
PLUGIN_ID="oris-dev-employee"
PLUGIN_VERSION="0.1.0"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_SERVICE="openclaw-gateway.service"
OPENCLAW_PORT="18789"
ENQUEUE_PORT="18891"
INTAKE_PORT="18892"
WEB_CONSOLE_PORT="18893"
DOMAIN="control.orisfy.com"
MARKER_FILE="$HOME/.openclaw/private/oris-dev-employee-plugin-install-current.json"
READINESS_COMMIT="a63dd823ac4d5b3fa0fa867771f94904d0b4ceee"
READINESS_JSON_REL="logs/dev_employee/openclaw_readonly_tool_readiness/openclaw-readonly-tool-readiness-20260618T212757Z.json"
EXPECTED_PRODUCT_COMMIT="bcb93e17ea88704548101f5e4a5c460e15a80ec7"
TOOL_1="oris_queue_status"
TOOL_2="oris_task_status"
TOOL_3="oris_latest_task_status"
HOOK_1="model_call_ended"
HOOK_2="after_tool_call"
HOOK_3="agent_end"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-readonly-enable-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/enablement.log"
RESULT_JSON="$TMP_ROOT/enablement.json"
FINAL_DETAILS_JSON="$TMP_ROOT/final-details.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
BACKUP_DIR="$HOME/.openclaw/backups/readonly-tool-enable-$STAMP"
CONFIG_BACKUP_FILE="$BACKUP_DIR/openclaw.json.tools-denied.bak"
MARKER_BACKUP_FILE="$BACKUP_DIR/oris-dev-employee-marker.tools-denied.bak"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_readonly_tool_enablement"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/openclaw-readonly-tool-enablement-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/openclaw-readonly-tool-enablement-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
NEXT_ACTION="INSPECT_READ_ONLY_ENABLEMENT_FAILURE"
SELECTED_POLICY_MODE="NONE"
MUTATION_STARTED="NO"
ROLLBACK_COUNT=0
ROLLBACK_HEALTHY="NOT_REQUIRED"
DIRECT_TOOL_CALLS_PASS="NO"
BROWSER_ACCEPTANCE_PASS="NO"
TELEMETRY_PRIVACY_PASS="NO"
QUEUE_UNCHANGED="NO"
PRODUCT_UNCHANGED="NO"
CONFIG_SCOPE_VALID="NO"
WRITE_TOOLS_ABSENT="NO"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
CHECK_TOTAL=0
CHECK_PASS=0
CHECK_FAIL=0

umask 077
mkdir -p "$TMP_ROOT"
: > "$RUN_LOG"

cleanup() {
  if [ -d "$WORKTREE" ]; then
    git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

log() { printf '%s\n' "$*" >> "$RUN_LOG"; }

record_check() {
  local name="$1" status="$2" detail="$3"
  CHECK_TOTAL=$((CHECK_TOTAL + 1))
  if [ "$status" = "PASS" ]; then CHECK_PASS=$((CHECK_PASS + 1)); else CHECK_FAIL=$((CHECK_FAIL + 1)); status="FAIL"; fi
  log "CHECK|$name|$status|$detail"
}

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "SELECTED_POLICY_MODE=$SELECTED_POLICY_MODE"
  echo "CHECKS_TOTAL=$CHECK_TOTAL"
  echo "CHECKS_PASS=$CHECK_PASS"
  echo "CHECKS_FAIL=$CHECK_FAIL"
  echo "DIRECT_TOOL_CALLS_PASS=$DIRECT_TOOL_CALLS_PASS"
  echo "BROWSER_ACCEPTANCE_PASS=$BROWSER_ACCEPTANCE_PASS"
  echo "TELEMETRY_PRIVACY_PASS=$TELEMETRY_PRIVACY_PASS"
  echo "CONFIG_SCOPE_VALID=$CONFIG_SCOPE_VALID"
  echo "QUEUE_UNCHANGED=$QUEUE_UNCHANGED"
  echo "PRODUCT_UNCHANGED=$PRODUCT_UNCHANGED"
  echo "WRITE_TOOLS_ABSENT=$WRITE_TOOLS_ABSENT"
  echo "ROLLBACK_COUNT=$ROLLBACK_COUNT"
  echo "ROLLBACK_HEALTHY=$ROLLBACK_HEALTHY"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "WRITE_TOOLS_ADDED=NO"
  echo "OPENCLAW_REINSTALLED_OR_UPGRADED=NO"
  echo "EVIDENCE_LOG=$EVIDENCE_LOG_REL"
  echo "EVIDENCE_JSON=$EVIDENCE_JSON_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

queue_fingerprint() {
  python3 - "$ORIS_REPO/orchestration/dev_employee_queue" <<'PY'
import hashlib,sys
from pathlib import Path
root=Path(sys.argv[1]); rows=[]
if root.exists():
 for path in sorted(root.glob('*.json')):
  try: rows.append(f"{path.name}\t{hashlib.sha256(path.read_bytes()).hexdigest()}")
  except (FileNotFoundError,PermissionError): rows.append(f"{path.name}\t<unreadable>")
print(hashlib.sha256('\n'.join(rows).encode()).hexdigest())
PY
}

active_queue_count() {
  find "$ORIS_REPO/orchestration/dev_employee_queue" -maxdepth 1 -type f \
    \( -name '*.queued.json' -o -name '*.running.json' -o -name '*.claimed.json' \
       -o -name '*.planning.json' -o -name '*.executing.json' -o -name '*.committing.json' \
       -o -name '*.pushing.json' -o -name '*.cancelling.json' \) 2>/dev/null \
    | wc -l | tr -d ' '
}

loopback_only() {
  local port="$1"
  python3 - "$port" <<'PY'
import subprocess,sys
port=sys.argv[1]
p=subprocess.run(['ss','-ltnH'],capture_output=True,text=True)
if p.returncode: print('UNKNOWN'); raise SystemExit(0)
rows=[]
for line in p.stdout.splitlines():
 parts=line.split()
 if len(parts)>=4 and (parts[3].endswith(':'+port) or parts[3].endswith(']:'+port)): rows.append(parts[3])
if not rows: print('NO_LISTENER')
elif all(x.startswith('127.0.0.1:') or x.startswith('[::1]:') for x in rows): print('YES')
else: print('NO')
PY
}

restart_gateway_and_wait() {
  systemctl --user restart "$OPENCLAW_SERVICE" >> "$RUN_LOG" 2>&1 || return 1
  local state="" status="000"
  for attempt in $(seq 1 30); do
    state="$(systemctl --user is-active "$OPENCLAW_SERVICE" 2>/dev/null || true)"
    status="$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
    if [ "$state" = "active" ] && [ "$status" = "200" ]; then return 0; fi
    sleep 1
  done
  return 1
}

verify_public_and_restricted_routes() {
  local direct_status public_status admin_status shell_status direct_sha public_sha
  direct_status="$(curl -sS --max-time 8 -o "$TMP_ROOT/direct-route.body" -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
  public_status="$(curl -sS -k --max-time 8 -H 'Cache-Control: no-cache' -o "$TMP_ROOT/public-route.body" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
  admin_status="$(curl -sS -k --max-time 8 -o /dev/null -w '%{http_code}' "https://$DOMAIN/admin" 2>/dev/null || true)"
  shell_status="$(curl -sS -k --max-time 8 -o /dev/null -w '%{http_code}' "https://$DOMAIN/_oris-chat-shell" 2>/dev/null || true)"
  direct_sha="$(sha256sum "$TMP_ROOT/direct-route.body" 2>/dev/null | awk '{print $1}')"
  public_sha="$(sha256sum "$TMP_ROOT/public-route.body" 2>/dev/null | awk '{print $1}')"
  [ "$direct_status" = "200" ] && [ "$public_status" = "200" ] && [ -n "$direct_sha" ] && [ "$direct_sha" = "$public_sha" ] || return 1
  case "$admin_status" in 401|403|404) ;; *) return 1 ;; esac
  case "$shell_status" in 401|403|404) ;; *) return 1 ;; esac
  return 0
}

config_has_tools_denied() {
  python3 - "$OPENCLAW_CONFIG" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY'
import json,sys
from pathlib import Path
data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
tools=data.get('tools') if isinstance(data.get('tools'),dict) else {}
deny=tools.get('deny') if isinstance(tools.get('deny'),list) else []
expected=set(sys.argv[2:5])
raise SystemExit(0 if expected.issubset(set(deny)) else 1)
PY
}

restore_tools_denied() {
  if [ ! -f "$CONFIG_BACKUP_FILE" ]; then ROLLBACK_HEALTHY="NO"; return 1; fi
  cp "$CONFIG_BACKUP_FILE" "$OPENCLAW_CONFIG" >/dev/null 2>&1 || { ROLLBACK_HEALTHY="NO"; return 1; }
  chmod 600 "$OPENCLAW_CONFIG" >/dev/null 2>&1 || { ROLLBACK_HEALTHY="NO"; return 1; }
  if [ -f "$MARKER_BACKUP_FILE" ]; then
    cp "$MARKER_BACKUP_FILE" "$MARKER_FILE" >/dev/null 2>&1 || { ROLLBACK_HEALTHY="NO"; return 1; }
    chmod 600 "$MARKER_FILE" >/dev/null 2>&1 || { ROLLBACK_HEALTHY="NO"; return 1; }
  fi
  restart_gateway_and_wait || { ROLLBACK_HEALTHY="NO"; return 1; }
  config_has_tools_denied || { ROLLBACK_HEALTHY="NO"; return 1; }
  ROLLBACK_COUNT=$((ROLLBACK_COUNT + 1))
  ROLLBACK_HEALTHY="YES"
  MUTATION_STARTED="NO"
  log "ROLLBACK|PASS|tools_denied_restored"
  return 0
}

build_evidence_json() {
  export TASK_ID STAMP RESULT FAILURE_CODE NEXT_ACTION SELECTED_POLICY_MODE CHECK_TOTAL CHECK_PASS CHECK_FAIL
  export DIRECT_TOOL_CALLS_PASS BROWSER_ACCEPTANCE_PASS TELEMETRY_PRIVACY_PASS CONFIG_SCOPE_VALID QUEUE_UNCHANGED PRODUCT_UNCHANGED WRITE_TOOLS_ABSENT
  export ROLLBACK_COUNT ROLLBACK_HEALTHY EVIDENCE_LOG_REL EVIDENCE_JSON_REL
  python3 - "$RESULT_JSON" "$RUN_LOG" "$FINAL_DETAILS_JSON" <<'PY'
import json,os,sys
from pathlib import Path
out,log_path,details_path=map(Path,sys.argv[1:])
checks=[]
for line in log_path.read_text(encoding='utf-8',errors='replace').splitlines():
 if line.startswith('CHECK|'):
  _,name,status,detail=line.split('|',3); checks.append({'name':name,'status':status,'detail':detail})
try: details=json.loads(details_path.read_text(encoding='utf-8'))
except Exception: details={}
payload={
 'task_id':os.environ['TASK_ID'],'checked_at':os.environ['STAMP'],'result':os.environ['RESULT'],
 'failure_code':os.environ.get('FAILURE_CODE') or None,'selected_policy_mode':os.environ['SELECTED_POLICY_MODE'],
 'checks':checks,'check_summary':{'total':int(os.environ['CHECK_TOTAL']),'pass':int(os.environ['CHECK_PASS']),'fail':int(os.environ['CHECK_FAIL'])},
 'direct_tool_calls_pass':os.environ['DIRECT_TOOL_CALLS_PASS']=='YES',
 'browser_acceptance_pass':os.environ['BROWSER_ACCEPTANCE_PASS']=='YES',
 'telemetry_privacy_pass':os.environ['TELEMETRY_PRIVACY_PASS']=='YES',
 'config_scope_valid':os.environ['CONFIG_SCOPE_VALID']=='YES',
 'queue_unchanged':os.environ['QUEUE_UNCHANGED']=='YES','product_unchanged':os.environ['PRODUCT_UNCHANGED']=='YES',
 'write_tools_absent':os.environ['WRITE_TOOLS_ABSENT']=='YES',
 'rollback':{'count':int(os.environ['ROLLBACK_COUNT']),'healthy':os.environ['ROLLBACK_HEALTHY']},
 'details':details,
 'safety':{'product_task_submitted':False,'write_tools_added':False,'openclaw_reinstalled_or_upgraded':False,'secret_values_recorded':False,'conversation_content_committed':False},
 'next_action':os.environ['NEXT_ACTION'],
 'evidence':{'log_path':os.environ['EVIDENCE_LOG_REL'],'json_path':os.environ['EVIDENCE_JSON_REL'],'self_commit_sha_omitted_to_prevent_post_commit_log_drift':True},
}
out.write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
PY
}

scan_evidence_safe() {
  python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY'
import re,sys
from pathlib import Path
patterns=[
 re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),
 re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
 re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
 re.compile(r'Bearer\s+[A-Za-z0-9._~+/=-]{12,}',re.I),
 re.compile(r'"(?:token|password|secret|credential|authorization|cookie|prompt|messages?|content|toolArguments?|toolResults?)"\s*:',re.I),
]
for f in sys.argv[1:]:
 text=Path(f).read_text(encoding='utf-8',errors='replace')
 if any(p.search(text) for p in patterns): raise SystemExit(1)
PY
}

commit_evidence() {
  build_evidence_json || return 1
  scan_evidence_safe || return 1
  git -C "$ORIS_REPO" fetch origin main >/dev/null 2>&1 || return 1
  git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >/dev/null 2>&1 || return 1
  mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL" || return 1
  cp "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" || return 1
  cp "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" || return 1
  git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || return 1
  git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || return 1
  git -C "$WORKTREE" commit -m "chore(dev-employee): record read-only tool enablement $STAMP" >/dev/null 2>&1 || return 1
  git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || return 1
  if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
    git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || return 1
  fi
  EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
  git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || return 1
  local remote
  remote="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
  [ -n "$EVIDENCE_COMMIT" ] && [ "$remote" = "$EVIDENCE_COMMIT" ] || return 1
  EVIDENCE_REMOTE_VERIFIED="YES"
  return 0
}

fatal() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  log "FATAL|$FAILURE_CODE|$NEXT_ACTION"
  if [ "$MUTATION_STARTED" = "YES" ]; then restore_tools_denied || true; fi
  [ -f "$FINAL_DETAILS_JSON" ] || printf '{}\n' > "$FINAL_DETAILS_JSON"
  commit_evidence || true
  summary
  exit 1
}
