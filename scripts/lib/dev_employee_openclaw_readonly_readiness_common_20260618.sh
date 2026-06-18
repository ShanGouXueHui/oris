#!/usr/bin/env bash

TASK_ID="commercial-openclaw-readonly-tool-enable-20260618"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
PLUGIN_REL="orchestration/openclaw_plugins/oris-dev-employee"
PLUGIN_ID="oris-dev-employee"
PLUGIN_VERSION="0.1.0"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_SERVICE="openclaw-gateway.service"
EXPECTED_OPENCLAW_VERSION="2026.5.19"
EXPECTED_PLUGIN_SOURCE_COMMIT="8f174b49196aac90b505846200ce260f75355b41"
EXPECTED_ARTIFACT_SHA256="976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda"
EXPECTED_PRODUCT_COMMIT="bcb93e17ea88704548101f5e4a5c460e15a80ec7"
EXPECTED_BACKUP="$HOME/.openclaw/backups/native-plugin-install-20260618T205656Z/openclaw.json.before.bak"
MARKER_FILE="$HOME/.openclaw/private/oris-dev-employee-plugin-install-current.json"
DOMAIN="control.orisfy.com"
OPENCLAW_PORT="18789"
ENQUEUE_PORT="18891"
INTAKE_PORT="18892"
WEB_CONSOLE_PORT="18893"
TOOL_1="oris_queue_status"
TOOL_2="oris_task_status"
TOOL_3="oris_latest_task_status"
HOOK_1="model_call_ended"
HOOK_2="after_tool_call"
HOOK_3="agent_end"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-readonly-readiness-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/readiness.log"
RESULT_JSON="$TMP_ROOT/readiness.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_readonly_tool_readiness"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/openclaw-readonly-tool-readiness-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/openclaw-readonly-tool-readiness-$STAMP.json"

RESULT="REVIEW"
FAILURE_CODE=""
NEXT_ACTION="READ_READINESS_EVIDENCE_BEFORE_ENABLEMENT"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
CHECK_TOTAL=0
CHECK_PASS=0
CHECK_REVIEW=0
CHECK_FAIL=0

umask 077
: > "$RUN_LOG"

cleanup() {
  if [ -d "$WORKTREE" ]; then
    git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

log() {
  printf '%s\n' "$*" >> "$RUN_LOG"
}

record_check() {
  local name="$1"
  local status="$2"
  local detail="$3"
  CHECK_TOTAL=$((CHECK_TOTAL + 1))
  case "$status" in
    PASS) CHECK_PASS=$((CHECK_PASS + 1)) ;;
    REVIEW) CHECK_REVIEW=$((CHECK_REVIEW + 1)) ;;
    FAIL) CHECK_FAIL=$((CHECK_FAIL + 1)) ;;
    *) status="FAIL"; CHECK_FAIL=$((CHECK_FAIL + 1)); detail="invalid_check_status" ;;
  esac
  log "CHECK|$name|$status|$detail"
}

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "READINESS_CHECKS_TOTAL=$CHECK_TOTAL"
  echo "READINESS_CHECKS_PASS=$CHECK_PASS"
  echo "READINESS_CHECKS_REVIEW=$CHECK_REVIEW"
  echo "READINESS_CHECKS_FAIL=$CHECK_FAIL"
  echo "CONFIG_MUTATED=NO"
  echo "GATEWAY_RESTARTED_OR_RELOADED=NO"
  echo "TOOLS_ENABLED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "WRITE_TOOLS_PRESENT=NO"
  echo "EVIDENCE_LOG=$EVIDENCE_LOG_REL"
  echo "EVIDENCE_JSON=$EVIDENCE_JSON_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fatal() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  log "FATAL|$FAILURE_CODE|$NEXT_ACTION"
  summary
  exit 1
}

file_owner_mode() {
  local path="$1"
  if [ ! -e "$path" ]; then
    echo "missing"
    return
  fi
  stat -c '%U:%a' "$path" 2>/dev/null || echo "unknown"
}

queue_fingerprint() {
  python3 - "$ORIS_REPO/orchestration/dev_employee_queue" <<'PY_QUEUE'
import hashlib, sys
from pathlib import Path
root = Path(sys.argv[1])
rows = []
if root.exists():
    for path in sorted(root.glob('*.json')):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append(f"{path.name}\t{digest}")
        except (FileNotFoundError, PermissionError):
            rows.append(f"{path.name}\t<unreadable>")
print(hashlib.sha256('\n'.join(rows).encode()).hexdigest())
PY_QUEUE
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
  python3 - "$port" <<'PY_LISTENER'
import subprocess, sys
port = sys.argv[1]
proc = subprocess.run(['ss','-ltnH'], text=True, capture_output=True)
if proc.returncode != 0:
    print('UNKNOWN')
    raise SystemExit(0)
listeners=[]
for line in proc.stdout.splitlines():
    parts=line.split()
    if len(parts) < 4:
        continue
    local=parts[3]
    if local.endswith(':'+port) or local.endswith(']:'+port):
        listeners.append(local)
if not listeners:
    print('NO_LISTENER')
elif all(x.startswith('127.0.0.1:') or x.startswith('[::1]:') for x in listeners):
    print('YES')
else:
    print('NO')
PY_LISTENER
}

for cmd in git openclaw python3 sha256sum systemctl curl ss stat find wc awk grep sed tr; do
  command -v "$cmd" >/dev/null 2>&1 || fatal "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done

[ "$(id -un 2>/dev/null)" = "admin" ] || fatal "wrong_linux_user" "RUN_AS_ADMIN"
[ -d "$ORIS_REPO/.git" ] || fatal "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fatal "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$OPENCLAW_CONFIG" ] || fatal "openclaw_config_missing" "RESTORE_OPENCLAW_CONFIG"

log "checked_at=$(date -Is)"
log "task_id=$TASK_ID"
log "mode=READ_ONLY_READINESS_NO_CONFIG_MUTATION"
log "config_mutated=NO"
log "gateway_restarted_or_reloaded=NO"
log "tools_enabled=NO"
log "product_task_submitted=NO"
log "secret_values_recorded=NO"

# Capture immutable before-state fingerprints. No configuration content is logged.
OPENCLAW_CONFIG_SHA_BEFORE="$(sha256sum "$OPENCLAW_CONFIG" 2>/dev/null | awk '{print $1}')"
OPENCLAW_PID_BEFORE="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"
GATEWAY_STATE_BEFORE="$(systemctl --user is-active "$OPENCLAW_SERVICE" 2>/dev/null || true)"
QUEUE_FINGERPRINT_BEFORE="$(queue_fingerprint)"
ACTIVE_QUEUE_COUNT_BEFORE="$(active_queue_count)"
ORIS_HEAD_BEFORE="$(git -C "$ORIS_REPO" rev-parse HEAD 2>/dev/null || true)"
ORIS_STATUS_BEFORE_FILE="$TMP_ROOT/oris-status-before.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_BEFORE_FILE" 2>/dev/null || fatal "oris_status_capture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_SHA_BEFORE="$(sha256sum "$ORIS_STATUS_BEFORE_FILE" | awk '{print $1}')"
PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE_FILE="$TMP_ROOT/product-status-before.bin"
git -C "$PRODUCT_REPO" status --porcelain=v1 -z --untracked-files=all > "$PRODUCT_STATUS_BEFORE_FILE" 2>/dev/null || fatal "product_status_capture_failed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_STATUS_SHA_BEFORE="$(sha256sum "$PRODUCT_STATUS_BEFORE_FILE" | awk '{print $1}')"
PRODUCT_TREE_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"

