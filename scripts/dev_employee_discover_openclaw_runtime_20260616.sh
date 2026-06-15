#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_DIR="$ORIS/logs/dev_employee/openclaw_discovery"
RUN_LOG="$LOG_DIR/openclaw-runtime-discovery-$STAMP.log"
JSON_LOG="$LOG_DIR/openclaw-runtime-discovery-$STAMP.json"
GIT_OUTPUT="/tmp/oris-openclaw-discovery-git-$STAMP.log"

RESULT="FAILED"
BINARY_FOUND="NO"
SERVICE_FOUND="NO"
PROCESS_FOUND="NO"
LISTENER_FOUND="NO"
ENDPOINT_DISCOVERED="NO"
CONFIG_KEYS_ONLY="NOT_RUN"
LOCAL_STASH="NONE"
LOCAL_STASH_RESTORE="NOT_NEEDED"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_OPENCLAW_DISCOVERY"

mkdir -p "$LOG_DIR"
: > "$RUN_LOG"

log() {
  printf '%s\n' "$*" | tee -a "$RUN_LOG"
}

sanitize() {
  sed -E \
    -e 's/(--?(token|api[-_]?key|secret|password|credential)[=[:space:]]+)[^[:space:]]+/\1<redacted>/Ig' \
    -e 's/(Authorization:[[:space:]]*(Bearer|Basic)[[:space:]]+)[^[:space:]]+/\1<redacted>/Ig' \
    -e 's#(https?://[^:/[:space:]]+:)[^@/[:space:]]+@#\1<redacted>@#g'
}

service_state() {
  systemctl --user is-active "$1" 2>/dev/null || true
}

restore_stash() {
  if [ "$LOCAL_STASH" = "CREATED" ]; then
    git stash pop >> "$RUN_LOG" 2>&1
    if [ "$?" -eq 0 ]; then
      LOCAL_STASH="RESTORED"
      LOCAL_STASH_RESTORE="PASS"
    else
      LOCAL_STASH_RESTORE="FAILED"
    fi
  fi
}

write_json() {
  python3 - "$RUN_LOG" "$JSON_LOG" <<'PY'
import json
import re
import sys
from pathlib import Path

run_log=Path(sys.argv[1])
out=Path(sys.argv[2])
text=run_log.read_text(encoding='utf-8', errors='replace')

def value(name, default=''):
    matches=re.findall(rf'^{re.escape(name)}=(.*)$', text, re.M)
    return matches[-1].strip() if matches else default

listeners=[]
for line in text.splitlines():
    if line.startswith('OPENCLAW_LISTENER='):
        listeners.append(line.split('=',1)[1])
probes=[]
for line in text.splitlines():
    if line.startswith('OPENCLAW_HTTP_PROBE='):
        probes.append(line.split('=',1)[1])
payload={
    'checked_at': value('CHECKED_AT'),
    'result': value('RESULT','FAILED'),
    'failure_code': value('FAILURE_CODE'),
    'binary_found': value('BINARY_FOUND') == 'YES',
    'binary_path': value('OPENCLAW_BINARY_PATH') or None,
    'binary_version': value('OPENCLAW_BINARY_VERSION') or None,
    'service_found': value('SERVICE_FOUND') == 'YES',
    'service_names': [item for item in value('OPENCLAW_SERVICE_NAMES').split(',') if item],
    'process_found': value('PROCESS_FOUND') == 'YES',
    'listener_found': value('LISTENER_FOUND') == 'YES',
    'listeners': listeners,
    'http_probes': probes,
    'endpoint_discovered': value('ENDPOINT_DISCOVERED') == 'YES',
    'endpoint_candidate': value('OPENCLAW_ENDPOINT_CANDIDATE') or None,
    'config_key_scan': value('CONFIG_KEYS_ONLY'),
    'real_product_task_submitted': False,
    'services_changed': False,
    'next_action': value('NEXT_ACTION'),
}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY
}

commit_logs() {
  local files=("${RUN_LOG#$ORIS/}" "${JSON_LOG#$ORIS/}")
  git add -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || {
    LOG_COMMIT="LOG_ADD_FAILED"
    return 1
  }
  git diff --cached --quiet -- "${files[@]}"
  local rc="$?"
  if [ "$rc" -eq 0 ]; then
    LOG_COMMIT="NO_LOG_CHANGES"
    return 0
  fi
  [ "$rc" -eq 1 ] || {
    LOG_COMMIT="LOG_DIFF_FAILED"
    return 1
  }
  git commit --only -m "chore(dev-employee): record OpenClaw runtime discovery $STAMP" -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || {
    LOG_COMMIT="LOG_COMMIT_FAILED"
    return 1
  }
  git push origin main > "$GIT_OUTPUT" 2>&1 || {
    LOG_COMMIT="LOG_PUSH_FAILED"
    return 1
  }
  LOG_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  return 0
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=discover-openclaw-runtime-20260616"
  echo "BINARY_FOUND=$BINARY_FOUND"
  echo "SERVICE_FOUND=$SERVICE_FOUND"
  echo "PROCESS_FOUND=$PROCESS_FOUND"
  echo "LISTENER_FOUND=$LISTENER_FOUND"
  echo "ENDPOINT_DISCOVERED=$ENDPOINT_DISCOVERED"
  echo "CONFIG_KEYS_ONLY=$CONFIG_KEYS_ONLY"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "BRIDGE_SERVICE=$(service_state oris-dev-employee-bridge.service)"
  echo "INTAKE_SERVICE=$(service_state oris-dev-employee-intake.service)"
  echo "WEB_CONSOLE_SERVICE=$(service_state oris-dev-employee-web-console.service)"
  echo "LOCAL_STASH=$LOCAL_STASH"
  echo "LOCAL_STASH_RESTORE=$LOCAL_STASH_RESTORE"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "SERVICES_CHANGED=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

if [ "$(id -un)" != "admin" ]; then
  FAILURE_CODE="wrong_linux_user"
  NEXT_ACTION="RUN_AS_ADMIN"
  RESULT="FAILED"
  log "CHECKED_AT=$(date -Is)"
  log "RESULT=$RESULT"
  log "FAILURE_CODE=$FAILURE_CODE"
  log "NEXT_ACTION=$NEXT_ACTION"
  write_json
  summary
  exit 1
fi

cd "$ORIS" || {
  FAILURE_CODE="oris_directory_missing"
  NEXT_ACTION="RESTORE_ORIS_REPOSITORY"
  RESULT="FAILED"
  log "CHECKED_AT=$(date -Is)"
  log "RESULT=$RESULT"
  log "FAILURE_CODE=$FAILURE_CODE"
  log "NEXT_ACTION=$NEXT_ACTION"
  write_json
  summary
  exit 1
}

TRACKED_DIRTY="$(git status --porcelain --untracked-files=no)"
if [ -n "$TRACKED_DIRTY" ]; then
  git stash push -m "temp-before-openclaw-discovery-$STAMP" -- . >> "$RUN_LOG" 2>&1
  if [ "$?" -ne 0 ]; then
    FAILURE_CODE="tracked_change_stash_failed"
    NEXT_ACTION="INSPECT_GIT_STATE"
    RESULT="FAILED"
    log "CHECKED_AT=$(date -Is)"
    log "RESULT=$RESULT"
    log "FAILURE_CODE=$FAILURE_CODE"
    log "NEXT_ACTION=$NEXT_ACTION"
    write_json
    summary
    exit 1
  fi
  LOCAL_STASH="CREATED"
fi

git fetch origin main >> "$RUN_LOG" 2>&1
if [ "$?" -ne 0 ]; then
  FAILURE_CODE="oris_fetch_failed"
else
  git rebase origin/main >> "$RUN_LOG" 2>&1
  [ "$?" -eq 0 ] || FAILURE_CODE="oris_rebase_failed"
fi
if [ -n "$FAILURE_CODE" ]; then
  NEXT_ACTION="INSPECT_ORIS_GIT_STATE"
  restore_stash
  RESULT="FAILED"
  log "CHECKED_AT=$(date -Is)"
  log "RESULT=$RESULT"
  log "FAILURE_CODE=$FAILURE_CODE"
  log "NEXT_ACTION=$NEXT_ACTION"
  write_json
  commit_logs || true
  summary
  exit 1
fi

log "===== OpenClaw binary discovery ====="
BINARY_PATH=""
for candidate in \
  "$(command -v openclaw 2>/dev/null || true)" \
  "$HOME/.local/bin/openclaw" \
  "$HOME/.npm-global/bin/openclaw" \
  "/usr/local/bin/openclaw" \
  "/usr/bin/openclaw"; do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    BINARY_PATH="$candidate"
    break
  fi
done
if [ -n "$BINARY_PATH" ]; then
  BINARY_FOUND="YES"
  VERSION="$($BINARY_PATH --version 2>&1 | head -n 3 | sanitize | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g')"
  log "OPENCLAW_BINARY_PATH=$BINARY_PATH"
  log "OPENCLAW_BINARY_VERSION=$VERSION"
  log "OPENCLAW_HELP_COMMANDS_START"
  "$BINARY_PATH" --help 2>&1 | head -n 120 | sanitize | tee -a "$RUN_LOG" >/dev/null
  log "OPENCLAW_HELP_COMMANDS_END"
else
  log "OPENCLAW_BINARY_PATH="
  log "OPENCLAW_BINARY_VERSION="
fi

log "===== OpenClaw user services ====="
SERVICE_NAMES="$(systemctl --user list-unit-files --type=service --no-legend 2>/dev/null | awk '{print $1}' | grep -Ei 'openclaw|(^|[-_.])claw' | sort -u || true)"
if [ -n "$SERVICE_NAMES" ]; then
  SERVICE_FOUND="YES"
  SERVICE_CSV="$(printf '%s\n' "$SERVICE_NAMES" | paste -sd, -)"
  log "OPENCLAW_SERVICE_NAMES=$SERVICE_CSV"
  while IFS= read -r service; do
    [ -n "$service" ] || continue
    log "OPENCLAW_SERVICE_BEGIN=$service"
    systemctl --user show "$service" \
      -p Id -p LoadState -p ActiveState -p SubState -p MainPID -p ExecStart -p FragmentPath -p DropInPaths -p EnvironmentFiles \
      --no-pager 2>&1 | sanitize | tee -a "$RUN_LOG" >/dev/null
    log "OPENCLAW_SERVICE_END=$service"
  done <<< "$SERVICE_NAMES"
else
  log "OPENCLAW_SERVICE_NAMES="
fi

log "===== OpenClaw processes ====="
PROCESS_LINES="$(ps -eo pid=,user=,comm=,args= 2>/dev/null | grep -Ei 'openclaw|(^|[ /_-])claw([ /_-]|$)' | grep -v -E 'grep|discover_openclaw_runtime' | sanitize || true)"
if [ -n "$PROCESS_LINES" ]; then
  PROCESS_FOUND="YES"
  printf '%s\n' "$PROCESS_LINES" | sed 's/^/OPENCLAW_PROCESS=/' | tee -a "$RUN_LOG" >/dev/null
fi

log "===== OpenClaw listeners ====="
PIDS="$(printf '%s\n' "$PROCESS_LINES" | awk '{print $1}' | grep -E '^[0-9]+$' | sort -u || true)"
PORTS=""
if [ -n "$PIDS" ]; then
  while IFS= read -r pid; do
    [ -n "$pid" ] || continue
    MATCHES="$(ss -ltnp 2>/dev/null | grep -F "pid=$pid," | sanitize || true)"
    if [ -n "$MATCHES" ]; then
      LISTENER_FOUND="YES"
      while IFS= read -r line; do
        [ -n "$line" ] || continue
        log "OPENCLAW_LISTENER=$line"
        port="$(printf '%s\n' "$line" | awk '{print $4}' | sed -E 's/.*:([0-9]+)$/\1/' | grep -E '^[0-9]+$' || true)"
        [ -n "$port" ] && PORTS="$PORTS $port"
      done <<< "$MATCHES"
    fi
  done <<< "$PIDS"
fi
PORTS="$(printf '%s\n' $PORTS 2>/dev/null | sort -nu | tr '\n' ' ')"

log "===== OpenClaw HTTP probes ====="
ENDPOINT_CANDIDATE=""
for port in $PORTS; do
  for path in /health /api/health /v1/health /; do
    code="$(curl -sS -m 3 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port$path" 2>/dev/null || true)"
    [ -n "$code" ] || code="000"
    log "OPENCLAW_HTTP_PROBE=http://127.0.0.1:$port$path status=$code"
    if [ "$code" != "000" ] && [ "$code" != "404" ] && [ -z "$ENDPOINT_CANDIDATE" ]; then
      ENDPOINT_CANDIDATE="http://127.0.0.1:$port"
    fi
  done
done
if [ -n "$ENDPOINT_CANDIDATE" ]; then
  ENDPOINT_DISCOVERED="YES"
fi
log "OPENCLAW_ENDPOINT_CANDIDATE=$ENDPOINT_CANDIDATE"

log "===== OpenClaw config file names and key names only ====="
python3 - "$HOME" <<'PY' | tee -a "$RUN_LOG" >/dev/null
import json
import re
import sys
from pathlib import Path

home=Path(sys.argv[1])
roots=[home/'.openclaw', home/'.config/openclaw', home/'.config/OpenClaw', Path('/etc/openclaw')]
key_pattern=re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*[:=]')
for root in roots:
    if not root.exists():
        continue
    print(f'OPENCLAW_CONFIG_ROOT={root}')
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        try:
            relative=path.relative_to(root)
        except ValueError:
            relative=path.name
        print(f'OPENCLAW_CONFIG_FILE={root}/{relative}')
        if path.stat().st_size > 1024*1024:
            print('OPENCLAW_CONFIG_KEYS=<file-too-large>')
            continue
        suffix=path.suffix.lower()
        keys=set()
        try:
            if suffix == '.json':
                data=json.loads(path.read_text(encoding='utf-8'))
                def walk(value, prefix=''):
                    if isinstance(value, dict):
                        for key, child in value.items():
                            name=f'{prefix}.{key}' if prefix else str(key)
                            keys.add(name)
                            walk(child, name)
                    elif isinstance(value, list):
                        for child in value[:3]:
                            walk(child, prefix+'[]')
                walk(data)
            elif suffix in {'.yaml','.yml','.toml','.ini','.conf','.env'}:
                for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
                    match=key_pattern.match(line)
                    if match:
                        keys.add(match.group(1))
        except Exception as exc:
            keys.add(f'<unreadable:{type(exc).__name__}>')
        if keys:
            print('OPENCLAW_CONFIG_KEYS='+','.join(sorted(keys)[:200]))
PY
CONFIG_KEYS_ONLY="PASS"

RESULT="PASS"
if [ "$BINARY_FOUND" = "YES" ] || [ "$SERVICE_FOUND" = "YES" ] || [ "$PROCESS_FOUND" = "YES" ]; then
  NEXT_ACTION="MAP_OPENCLAW_PROVIDER_CONTRACT_AND_DEPLOY_CHAT_V3"
else
  NEXT_ACTION="INSTALL_OR_REGISTER_OPENCLAW_RUNTIME"
fi

restore_stash
if [ "$LOCAL_STASH_RESTORE" = "FAILED" ]; then
  RESULT="FAILED"
  FAILURE_CODE="local_tracked_change_restore_failed"
  NEXT_ACTION="INSPECT_GIT_STASH"
fi

log "CHECKED_AT=$(date -Is)"
log "BINARY_FOUND=$BINARY_FOUND"
log "SERVICE_FOUND=$SERVICE_FOUND"
log "PROCESS_FOUND=$PROCESS_FOUND"
log "LISTENER_FOUND=$LISTENER_FOUND"
log "ENDPOINT_DISCOVERED=$ENDPOINT_DISCOVERED"
log "CONFIG_KEYS_ONLY=$CONFIG_KEYS_ONLY"
log "RESULT=$RESULT"
log "FAILURE_CODE=$FAILURE_CODE"
log "NEXT_ACTION=$NEXT_ACTION"
write_json
commit_logs || {
  RESULT="FAILED"
  FAILURE_CODE="discovery_evidence_push_failed"
  NEXT_ACTION="RESOLVE_ORIS_EVIDENCE_PUSH"
}
summary
rm -f "$GIT_OUTPUT"

if [ "$RESULT" = "PASS" ]; then
  exit 0
fi
exit 1
