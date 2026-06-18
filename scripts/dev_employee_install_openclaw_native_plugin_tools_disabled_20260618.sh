#!/usr/bin/env bash

TASK_ID="commercial-openclaw-native-plugin-install-20260618"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
PLUGIN_REL="orchestration/openclaw_plugins/oris-dev-employee"
PLUGIN_ID="oris-dev-employee"
PLUGIN_VERSION="0.1.0"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_SERVICE="openclaw-gateway.service"
EXPECTED_OPENCLAW_VERSION="2026.5.19"
EXPECTED_PRODUCT_COMMIT="bcb93e17ea88704548101f5e4a5c460e15a80ec7"
VALIDATION_EVIDENCE_COMMIT="fadb6275f0a348aed7692f4a910f341f69049363"
VALIDATION_EVIDENCE_REL="logs/dev_employee/openclaw_native_plugin_validation/openclaw-native-plugin-validation-20260618T153153Z.json"
DOMAIN="control.orisfy.com"
OPENCLAW_PORT="18789"
ENQUEUE_PORT="18891"
INTAKE_PORT="18892"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-plugin-install-${STAMP}-XXXXXX)"
ARCHIVE_ROOT="$TMP_ROOT/archive"
BUILD_ROOT="$ARCHIVE_ROOT/$PLUGIN_REL"
RUN_LOG="$TMP_ROOT/install.log"
RESULT_JSON="$TMP_ROOT/install.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
BACKUP_DIR="$HOME/.openclaw/backups/native-plugin-install-$STAMP"
BACKUP_FILE="$BACKUP_DIR/openclaw.json.before.bak"
PRIVATE_DIR="$HOME/.openclaw/private"
MARKER_FILE="$PRIVATE_DIR/oris-dev-employee-plugin-install-current.json"
FAILED_MARKER_FILE="$PRIVATE_DIR/oris-dev-employee-plugin-install-failed-$STAMP.json"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_native_plugin_install"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/openclaw-native-plugin-install-tools-disabled-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/openclaw-native-plugin-install-tools-disabled-$STAMP.json"
TOOL_1="oris_queue_status"
TOOL_2="oris_task_status"
TOOL_3="oris_latest_task_status"
HOOK_1="model_call_ended"
HOOK_2="after_tool_call"
HOOK_3="agent_end"

RESULT="FAILED"
FAILURE_CODE=""
SOURCE_COMMIT=""
VALIDATED_PLUGIN_TREE_MATCH="NO"
OPENCLAW_VERSION="unknown"
NODE_VERSION="unknown"
NPM_VERSION="unknown"
NPM_INSTALL="NOT_RUN"
TSC_BUILD="NOT_RUN"
UNIT_TESTS="NOT_RUN"
MIXED_PLUGIN_VALIDATE="NOT_RUN"
NPM_PACK="NOT_RUN"
ARTIFACT_FILE=""
ARTIFACT_SHA256=""
CONFIG_BACKUP_CREATED="NO"
TOOLS_DENY_APPLIED="NO"
TOOLS_ALLOW_UNCHANGED="NO"
AUTH_MODE="unknown"
AUTH_SECRET_UNCHANGED="NO"
PLUGIN_INSTALL_RC="not_run"
PLUGIN_ENABLE_RC="not_run"
GATEWAY_RESTART="NOT_RUN"
GATEWAY_STATE="unknown"
DIRECT_ROOT_STATUS="000"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ROOT_MATCHES_DIRECT="NO"
PLUGIN_ENABLED="NO"
PLUGIN_ERROR_COUNT="unknown"
RUNTIME_TOOL_COUNT="unknown"
RUNTIME_HOOK_COUNT="unknown"
RUNTIME_TOOLS_MATCH="NO"
RUNTIME_HOOKS_MATCH="NO"
WRITE_TOOLS_ABSENT="NO"
TOOLS_EFFECTIVELY_DENIED="NO"
ENQUEUE_LOOPBACK_ONLY="unknown"
INTAKE_LOOPBACK_ONLY="unknown"
QUEUE_STATE_UNCHANGED="NO"
ORIS_WORKTREE_PRESERVED="NO"
PRODUCT_BASELINE_PRESERVED="NO"
MARKER_WRITTEN="NO"
MUTATION_STARTED="NO"
ROLLBACK_PERFORMED="NO"
ROLLBACK_HEALTHY="unknown"
PRODUCT_TASK_SUBMITTED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_NATIVE_PLUGIN_INSTALL_FAILURE"

umask 077
mkdir -p "$ARCHIVE_ROOT"
: > "$RUN_LOG"

cleanup() {
  if [ -d "$WORKTREE" ]; then
    git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

log() { printf '%s\n' "$*" >> "$RUN_LOG"; }

plugin_present() {
  local output="$1"
  openclaw plugins list --json > "$output" 2>> "$RUN_LOG"
  if [ "$?" -ne 0 ]; then
    echo "unknown"
    return
  fi
  python3 - "$output" "$PLUGIN_ID" <<'PY_PLUGIN'
import json,sys
from pathlib import Path
try:
    data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
except Exception:
    print('unknown'); raise SystemExit(0)
plugins=data.get('plugins') if isinstance(data,dict) else []
found=False
if isinstance(plugins,list):
    for item in plugins:
        if isinstance(item,dict) and str(item.get('id') or item.get('name') or '')==sys.argv[2]:
            found=True; break
print('YES' if found else 'NO')
PY_PLUGIN
}

queue_fingerprint() {
  python3 - "$ORIS_REPO/orchestration/dev_employee_queue" <<'PY_QUEUE'
import hashlib,sys
from pathlib import Path
root=Path(sys.argv[1]); rows=[]
if root.exists():
    for path in sorted(root.glob('*.json')):
        try:
            s=path.stat(); rows.append(f"{path.name}\t{s.st_size}\t{s.st_mtime_ns}")
        except FileNotFoundError:
            pass
print(hashlib.sha256('\n'.join(rows).encode()).hexdigest())
PY_QUEUE
}

loopback_only() {
  local port="$1"
  local listener
  listener="$(ss -ltn 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" {print $4; exit}')"
  case "$listener" in
    127.0.0.1:*|\[::1\]:*) echo "YES" ;;
    *) echo "NO" ;;
  esac
}

perform_rollback() {
  if [ "$MUTATION_STARTED" != "YES" ]; then
    return
  fi
  log "AUTOMATIC_ROLLBACK_STARTED=$(date -Is)"
  if [ "$(plugin_present "$TMP_ROOT/plugins-rollback-before.json")" = "YES" ]; then
    openclaw plugins uninstall "$PLUGIN_ID" >> "$RUN_LOG" 2>&1 || true
  fi
  if [ -f "$BACKUP_FILE" ]; then
    cp "$BACKUP_FILE" "$OPENCLAW_CONFIG" >> "$RUN_LOG" 2>&1 || true
    chmod 600 "$OPENCLAW_CONFIG" >> "$RUN_LOG" 2>&1 || true
  fi
  systemctl --user restart "$OPENCLAW_SERVICE" >> "$RUN_LOG" 2>&1 || true
  local state=""
  local status="000"
  for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    state="$(systemctl --user is-active "$OPENCLAW_SERVICE" 2>/dev/null || true)"
    status="$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
    if [ "$state" = "active" ] && [ "$status" = "200" ]; then
      break
    fi
    sleep 1
  done
  local present
  present="$(plugin_present "$TMP_ROOT/plugins-rollback-after.json")"
  if [ "$state" = "active" ] && [ "$status" = "200" ] && [ "$present" = "NO" ]; then
    ROLLBACK_PERFORMED="YES"
    ROLLBACK_HEALTHY="YES"
  else
    ROLLBACK_PERFORMED="FAILED"
    ROLLBACK_HEALTHY="NO"
  fi
  if [ -f "$MARKER_FILE" ]; then
    mv "$MARKER_FILE" "$FAILED_MARKER_FILE" >> "$RUN_LOG" 2>&1 || true
    chmod 600 "$FAILED_MARKER_FILE" >> "$RUN_LOG" 2>&1 || true
  fi
  log "AUTOMATIC_ROLLBACK_FINISHED=$(date -Is)"
  log "ROLLBACK_PERFORMED=$ROLLBACK_PERFORMED"
  log "ROLLBACK_HEALTHY=$ROLLBACK_HEALTHY"
}

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "SOURCE_COMMIT=$SOURCE_COMMIT"
  echo "VALIDATED_PLUGIN_TREE_MATCH=$VALIDATED_PLUGIN_TREE_MATCH"
  echo "OPENCLAW_VERSION=$OPENCLAW_VERSION"
  echo "NODE_VERSION=$NODE_VERSION"
  echo "NPM_VERSION=$NPM_VERSION"
  echo "NPM_INSTALL=$NPM_INSTALL"
  echo "TSC_BUILD=$TSC_BUILD"
  echo "UNIT_TESTS=$UNIT_TESTS"
  echo "MIXED_PLUGIN_VALIDATE=$MIXED_PLUGIN_VALIDATE"
  echo "NPM_PACK=$NPM_PACK"
  echo "ARTIFACT_SHA256=$ARTIFACT_SHA256"
  echo "CONFIG_BACKUP_CREATED=$CONFIG_BACKUP_CREATED"
  echo "TOOLS_DENY_APPLIED=$TOOLS_DENY_APPLIED"
  echo "TOOLS_ALLOW_UNCHANGED=$TOOLS_ALLOW_UNCHANGED"
  echo "AUTH_MODE=$AUTH_MODE"
  echo "AUTH_SECRET_UNCHANGED=$AUTH_SECRET_UNCHANGED"
  echo "PLUGIN_INSTALL_RC=$PLUGIN_INSTALL_RC"
  echo "PLUGIN_ENABLE_RC=$PLUGIN_ENABLE_RC"
  echo "GATEWAY_RESTART=$GATEWAY_RESTART"
  echo "GATEWAY_STATE=$GATEWAY_STATE"
  echo "DIRECT_ROOT_STATUS=$DIRECT_ROOT_STATUS"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ROOT_MATCHES_DIRECT=$PUBLIC_ROOT_MATCHES_DIRECT"
  echo "PLUGIN_ENABLED=$PLUGIN_ENABLED"
  echo "PLUGIN_ERROR_COUNT=$PLUGIN_ERROR_COUNT"
  echo "RUNTIME_TOOL_COUNT=$RUNTIME_TOOL_COUNT"
  echo "RUNTIME_HOOK_COUNT=$RUNTIME_HOOK_COUNT"
  echo "RUNTIME_TOOLS_MATCH=$RUNTIME_TOOLS_MATCH"
  echo "RUNTIME_HOOKS_MATCH=$RUNTIME_HOOKS_MATCH"
  echo "WRITE_TOOLS_ABSENT=$WRITE_TOOLS_ABSENT"
  echo "TOOLS_EFFECTIVELY_DENIED=$TOOLS_EFFECTIVELY_DENIED"
  echo "ENQUEUE_LOOPBACK_ONLY=$ENQUEUE_LOOPBACK_ONLY"
  echo "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
  echo "QUEUE_STATE_UNCHANGED=$QUEUE_STATE_UNCHANGED"
  echo "ORIS_WORKTREE_PRESERVED=$ORIS_WORKTREE_PRESERVED"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "MARKER_WRITTEN=$MARKER_WRITTEN"
  echo "ROLLBACK_PERFORMED=$ROLLBACK_PERFORMED"
  echo "ROLLBACK_HEALTHY=$ROLLBACK_HEALTHY"
  echo "PRODUCT_TASK_SUBMITTED=$PRODUCT_TASK_SUBMITTED"
  echo "PLUGIN_INSTALLED_OR_ENABLED=$([ "$RESULT" = "INSTALLED_TOOLS_DENIED" ] && echo YES || echo NO)"
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
  perform_rollback
  summary
  exit 1
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user" "RUN_AS_ADMIN"; fi
for cmd in git openclaw npm node python3 sha256sum systemctl curl ss cp chmod mkdir stat tar awk grep find paste; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$OPENCLAW_CONFIG" ] || fail_now "openclaw_config_missing" "RESTORE_OPENCLAW_CONFIG"
[ "$(stat -c '%a' "$OPENCLAW_CONFIG" 2>/dev/null)" = "600" ] || fail_now "openclaw_config_not_0600" "RESTORE_OPENCLAW_CONFIG_PERMISSIONS"
[ ! -f "$MARKER_FILE" ] || fail_now "plugin_install_marker_already_exists" "REVIEW_EXISTING_PLUGIN_INSTALL_STATE"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=REVERSIBLE_NATIVE_PLUGIN_INSTALL_WITH_TOOLS_DENIED"
log "PLUGIN_ID=$PLUGIN_ID"
log "PRODUCT_TASK_SUBMITTED=NO"
log "OPENCLAW_REINSTALLED_OR_UPGRADED=NO"
log "SECRET_VALUES_RECORDED=NO"

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
SOURCE_COMMIT="$(git -C "$ORIS_REPO" rev-parse origin/main 2>/dev/null || true)"
[ -n "$SOURCE_COMMIT" ] || fail_now "origin_main_unresolved" "REPAIR_GITHUB_CONNECTIVITY"

VALIDATION_RESULT="$(git -C "$ORIS_REPO" show "$VALIDATION_EVIDENCE_COMMIT:$VALIDATION_EVIDENCE_REL" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("result", ""))' 2>/dev/null || true)"
[ "$VALIDATION_RESULT" = "VALIDATED_NOT_INSTALLED" ] || fail_now "validation_evidence_not_authoritative" "RESTORE_VALIDATION_EVIDENCE"
VALIDATED_TREE="$(git -C "$ORIS_REPO" rev-parse "$VALIDATION_EVIDENCE_COMMIT:$PLUGIN_REL" 2>/dev/null || true)"
CURRENT_TREE="$(git -C "$ORIS_REPO" rev-parse "origin/main:$PLUGIN_REL" 2>/dev/null || true)"
if [ -n "$VALIDATED_TREE" ] && [ "$VALIDATED_TREE" = "$CURRENT_TREE" ]; then VALIDATED_PLUGIN_TREE_MATCH="YES"; fi
[ "$VALIDATED_PLUGIN_TREE_MATCH" = "YES" ] || fail_now "plugin_source_changed_since_validation" "RERUN_ISOLATED_PLUGIN_VALIDATION"

OPENCLAW_VERSION="$(openclaw --version 2>/dev/null | head -n 1 | tr -d '\r')"
NODE_VERSION="$(node --version 2>/dev/null || true)"
NPM_VERSION="$(npm --version 2>/dev/null || true)"
case "$OPENCLAW_VERSION" in *"$EXPECTED_OPENCLAW_VERSION"*) ;; *) fail_now "unexpected_openclaw_version" "REVIEW_PLUGIN_COMPATIBILITY" ;; esac

ACTIVE_QUEUE_COUNT="$(find "$ORIS_REPO/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' -o -name '*.claimed.json' -o -name '*.planning.json' -o -name '*.executing.json' -o -name '*.committing.json' -o -name '*.pushing.json' -o -name '*.cancelling.json' \) 2>/dev/null | wc -l | tr -d ' ')"
[ "$ACTIVE_QUEUE_COUNT" = "0" ] || fail_now "active_queue_present" "WAIT_FOR_QUEUE_TO_DRAIN"

PLUGIN_PRESENT_PRE="$(plugin_present "$TMP_ROOT/plugins-pre.json")"
[ "$PLUGIN_PRESENT_PRE" = "NO" ] || fail_now "plugin_already_present" "REVIEW_EXISTING_PLUGIN_STATE"

ORIS_STATUS_BEFORE_FILE="$TMP_ROOT/oris-status-before.bin"
ORIS_STATUS_AFTER_FILE="$TMP_ROOT/oris-status-after.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_BEFORE_FILE" || fail_now "oris_status_capture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_BEFORE_SHA="$(sha256sum "$ORIS_STATUS_BEFORE_FILE" | awk '{print $1}')"
QUEUE_BEFORE="$(queue_fingerprint)"
PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_head" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_remote_main" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ -z "$PRODUCT_STATUS_BEFORE" ] || fail_now "product_worktree_not_clean" "RESTORE_COMPLETED_PRODUCT_BASELINE"

OPENCLAW_CONFIG_HASH_BEFORE="$(sha256sum "$OPENCLAW_CONFIG" | awk '{print $1}')"
OPENCLAW_PID_BEFORE="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"
python3 - "$OPENCLAW_CONFIG" "$TMP_ROOT/config-before-safe.json" <<'PY_CONFIG_BEFORE'
import hashlib,json,sys
from pathlib import Path
data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
auth=data.get('gateway',{}).get('auth',{}) if isinstance(data.get('gateway'),dict) else {}
mode=auth.get('mode') or 'token'
secret=auth.get(mode)
if mode not in {'token','password'} or not isinstance(secret,str) or not secret:
    raise SystemExit(2)
tools=data.get('tools') if isinstance(data.get('tools'),dict) else {}
allow=tools.get('allow') if isinstance(tools.get('allow'),list) else []
Path(sys.argv[2]).write_text(json.dumps({
 'auth_mode':mode,
 'auth_secret_sha256':hashlib.sha256(secret.encode()).hexdigest(),
 'tools_allow':allow,
 'tools_allow_sha256':hashlib.sha256(json.dumps(allow,sort_keys=True).encode()).hexdigest(),
 'secret_values_recorded':False,
},indent=2)+'\n')
PY_CONFIG_BEFORE
[ "$?" -eq 0 ] || fail_now "openclaw_authenticated_mode_required" "RESTORE_GATEWAY_AUTH_CONFIGURATION"
AUTH_MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["auth_mode"])' "$TMP_ROOT/config-before-safe.json")"
AUTH_SECRET_SHA_BEFORE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["auth_secret_sha256"])' "$TMP_ROOT/config-before-safe.json")"
TOOLS_ALLOW_SHA_BEFORE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tools_allow_sha256"])' "$TMP_ROOT/config-before-safe.json")"

OPENCLAW_BIN="$(command -v openclaw)"
OPENCLAW_PACKAGE_ROOT="$(python3 - "$OPENCLAW_BIN" <<'PY_ROOT'
import json,sys
from pathlib import Path
start=Path(sys.argv[1]).resolve()
for parent in [start.parent,*start.parents]:
    package=parent/'package.json'
    if not package.is_file(): continue
    try: data=json.loads(package.read_text(encoding='utf-8'))
    except Exception: continue
    if data.get('name')=='openclaw': print(parent); raise SystemExit(0)
raise SystemExit(1)
PY_ROOT
)"
[ -n "$OPENCLAW_PACKAGE_ROOT" ] || fail_now "openclaw_package_root_not_found" "INSPECT_EXISTING_OPENCLAW_INSTALLATION"

git -C "$ORIS_REPO" archive origin/main "$PLUGIN_REL" | tar -x -C "$ARCHIVE_ROOT"
[ "$?" -eq 0 ] || fail_now "plugin_archive_failed" "INSPECT_ORIS_PLUGIN_SOURCE"
[ -f "$BUILD_ROOT/package.json" ] || fail_now "plugin_package_missing" "INSPECT_ORIS_PLUGIN_SOURCE"

if (cd "$BUILD_ROOT" && npm install --ignore-scripts --no-audit --no-fund --legacy-peer-deps) >> "$RUN_LOG" 2>&1; then NPM_INSTALL="PASS"; else NPM_INSTALL="FAIL"; fail_now "plugin_dependency_install_failed" "INSPECT_PLUGIN_BUILD_LOG"; fi
rm -rf "$BUILD_ROOT/node_modules/openclaw"
ln -s "$OPENCLAW_PACKAGE_ROOT" "$BUILD_ROOT/node_modules/openclaw" || fail_now "openclaw_sdk_link_failed" "INSPECT_OPENCLAW_PACKAGE_ROOT"
if (cd "$BUILD_ROOT" && npm run build) >> "$RUN_LOG" 2>&1; then TSC_BUILD="PASS"; else TSC_BUILD="FAIL"; fail_now "plugin_typescript_build_failed" "RERUN_PLUGIN_DIAGNOSTIC"; fi
if (cd "$BUILD_ROOT" && npm test) >> "$RUN_LOG" 2>&1; then UNIT_TESTS="PASS"; else UNIT_TESTS="FAIL"; fail_now "plugin_unit_tests_failed" "REPAIR_PLUGIN_TESTS"; fi
if (cd "$BUILD_ROOT" && npm run plugin:validate) >> "$RUN_LOG" 2>&1; then MIXED_PLUGIN_VALIDATE="PASS"; else MIXED_PLUGIN_VALIDATE="FAIL"; fail_now "mixed_plugin_validation_failed" "REPAIR_MIXED_PLUGIN_CONTRACT"; fi
if (cd "$BUILD_ROOT" && npm pack --json --ignore-scripts) > "$TMP_ROOT/npm-pack.json" 2>> "$RUN_LOG"; then NPM_PACK="PASS"; else NPM_PACK="FAIL"; fail_now "npm_pack_failed" "INSPECT_PLUGIN_PACKAGE_METADATA"; fi
PACK_FILENAME="$(python3 - "$TMP_ROOT/npm-pack.json" <<'PY_PACK'
import json,sys
from pathlib import Path
data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if not isinstance(data,list) or not data or not isinstance(data[0],dict): raise SystemExit(2)
name=data[0].get('filename')
if not isinstance(name,str) or not name: raise SystemExit(3)
print(name)
PY_PACK
)"
[ "$?" -eq 0 ] && [ -n "$PACK_FILENAME" ] || fail_now "npm_pack_output_invalid" "INSPECT_PLUGIN_PACKAGE_METADATA"
ARTIFACT_FILE="$BUILD_ROOT/$PACK_FILENAME"
[ -f "$ARTIFACT_FILE" ] || fail_now "npm_pack_artifact_missing" "INSPECT_PLUGIN_PACKAGE_METADATA"
ARTIFACT_SHA256="$(sha256sum "$ARTIFACT_FILE" | awk '{print $1}')"

mkdir -p "$BACKUP_DIR" "$PRIVATE_DIR" || fail_now "private_directory_create_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
chmod 700 "$BACKUP_DIR" "$PRIVATE_DIR" || fail_now "private_directory_permission_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
cp "$OPENCLAW_CONFIG" "$BACKUP_FILE" || fail_now "openclaw_config_backup_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
chmod 600 "$BACKUP_FILE" || fail_now "openclaw_config_backup_permission_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
CONFIG_BACKUP_CREATED="YES"

python3 - "$MARKER_FILE" "$BACKUP_FILE" "$PLUGIN_ID" "$PLUGIN_VERSION" "$SOURCE_COMMIT" "$ARTIFACT_SHA256" "$STAMP" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY_MARKER'
import json,os,sys
from pathlib import Path
path=Path(sys.argv[1])
payload={
 'state':'installing',
 'plugin_id':sys.argv[3],
 'plugin_version':sys.argv[4],
 'source_commit':sys.argv[5],
 'artifact_sha256':sys.argv[6],
 'installed_at':sys.argv[7],
 'config_backup':sys.argv[2],
 'denied_tools':sys.argv[8:11],
 'secret_values_recorded':False,
}
path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
os.chmod(path,0o600)
PY_MARKER
[ "$?" -eq 0 ] || fail_now "private_install_marker_create_failed" "CHECK_PRIVATE_DIRECTORY_PERMISSIONS"
MARKER_WRITTEN="YES"
MUTATION_STARTED="YES"

python3 - "$OPENCLAW_CONFIG" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY_DENY'
import json,os,sys
from pathlib import Path
path=Path(sys.argv[1]); names=sys.argv[2:]
data=json.loads(path.read_text(encoding='utf-8'))
tools=data.setdefault('tools',{})
if not isinstance(tools,dict): raise SystemExit(2)
deny=tools.get('deny')
if deny is None: deny=[]
if not isinstance(deny,list) or any(not isinstance(x,str) for x in deny): raise SystemExit(3)
for name in names:
    if name not in deny: deny.append(name)
tools['deny']=deny
tmp=path.with_name(path.name+'.oris-plugin.tmp')
tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
os.chmod(tmp,0o600); json.loads(tmp.read_text(encoding='utf-8')); os.replace(tmp,path); os.chmod(path,0o600)
PY_DENY
[ "$?" -eq 0 ] || fail_now "tools_deny_config_update_failed" "INSPECT_OPENCLAW_CONFIG"
TOOLS_DENY_APPLIED="YES"

openclaw plugins install "npm-pack:$ARTIFACT_FILE" >> "$RUN_LOG" 2>&1
PLUGIN_INSTALL_RC="$?"
[ "$PLUGIN_INSTALL_RC" = "0" ] || fail_now "plugin_install_failed" "INSPECT_OPENCLAW_PLUGIN_INSTALL_LOG"
openclaw plugins enable "$PLUGIN_ID" >> "$RUN_LOG" 2>&1
PLUGIN_ENABLE_RC="$?"
[ "$PLUGIN_ENABLE_RC" = "0" ] || fail_now "plugin_enable_failed" "INSPECT_OPENCLAW_PLUGIN_CONFIG"

if systemctl --user restart "$OPENCLAW_SERVICE" >> "$RUN_LOG" 2>&1; then GATEWAY_RESTART="PASS"; else GATEWAY_RESTART="FAIL"; fail_now "openclaw_gateway_restart_failed" "INSPECT_OPENCLAW_GATEWAY_JOURNAL"; fi

for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  GATEWAY_STATE="$(systemctl --user is-active "$OPENCLAW_SERVICE" 2>/dev/null || true)"
  DIRECT_ROOT_STATUS="$(curl -sS --max-time 5 -o "$TMP_ROOT/direct.body" -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
  PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 5 -H 'Cache-Control: no-cache' -o "$TMP_ROOT/public.body" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
  if [ "$GATEWAY_STATE" = "active" ] && [ "$DIRECT_ROOT_STATUS" = "200" ] && [ "$PUBLIC_ROOT_STATUS" = "200" ]; then break; fi
  sleep 1
done
[ "$GATEWAY_STATE" = "active" ] || fail_now "gateway_not_active_after_plugin_install" "INSPECT_OPENCLAW_GATEWAY_JOURNAL"
[ "$DIRECT_ROOT_STATUS" = "200" ] || fail_now "direct_root_unhealthy_after_plugin_install" "INSPECT_OPENCLAW_GATEWAY_JOURNAL"
[ "$PUBLIC_ROOT_STATUS" = "200" ] || fail_now "public_root_unhealthy_after_plugin_install" "INSPECT_PUBLIC_ROUTING"
DIRECT_SHA="$(sha256sum "$TMP_ROOT/direct.body" | awk '{print $1}')"
PUBLIC_SHA="$(sha256sum "$TMP_ROOT/public.body" | awk '{print $1}')"
if [ -n "$DIRECT_SHA" ] && [ "$DIRECT_SHA" = "$PUBLIC_SHA" ]; then PUBLIC_ROOT_MATCHES_DIRECT="YES"; fi
[ "$PUBLIC_ROOT_MATCHES_DIRECT" = "YES" ] || fail_now "public_root_no_longer_matches_direct" "INSPECT_PUBLIC_ROUTING"

openclaw plugins list --json > "$TMP_ROOT/plugins-list.json" 2>> "$RUN_LOG" || fail_now "plugin_list_failed_after_install" "INSPECT_OPENCLAW_PLUGIN_REGISTRY"
openclaw plugins inspect "$PLUGIN_ID" --runtime --json > "$TMP_ROOT/plugin-runtime.json" 2>> "$RUN_LOG" || fail_now "plugin_runtime_inspect_failed" "INSPECT_OPENCLAW_PLUGIN_RUNTIME"
openclaw plugins doctor > "$TMP_ROOT/plugin-doctor.txt" 2>&1
PLUGIN_DOCTOR_RC="$?"
[ "$PLUGIN_DOCTOR_RC" = "0" ] || fail_now "plugin_doctor_failed" "INSPECT_OPENCLAW_PLUGIN_DIAGNOSTICS"

python3 - "$TMP_ROOT/plugins-list.json" "$TMP_ROOT/plugin-runtime.json" "$TMP_ROOT/runtime-safe.json" "$PLUGIN_ID" "$TOOL_1" "$TOOL_2" "$TOOL_3" "$HOOK_1" "$HOOK_2" "$HOOK_3" <<'PY_RUNTIME'
import json,sys
from pathlib import Path
listing=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
runtime=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
plugin_id=sys.argv[4]; expected_tools=set(sys.argv[5:8]); expected_hooks=set(sys.argv[8:11])
plugins=listing.get('plugins') if isinstance(listing,dict) else []
enabled=False; errors=0
if isinstance(plugins,list):
    for item in plugins:
        if not isinstance(item,dict): continue
        pid=str(item.get('id') or item.get('name') or '')
        if pid!=plugin_id: continue
        enabled=item.get('enabled') is True
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
            elif low in {'hooks','registeredhooks','hooknames'}: add(x,hooks)
            walk(x)
    elif isinstance(v,list):
        for x in v: walk(x)
walk(runtime)
write_names={'oris_submit_task','oris_cancel_task','oris_retry_task'}
payload={
 'plugin_enabled':enabled,
 'plugin_error_count':errors,
 'runtime_tools':sorted(tools),
 'runtime_hooks':sorted(hooks),
 'runtime_tools_match':tools==expected_tools,
 'runtime_hooks_match':expected_hooks.issubset(hooks),
 'write_tools_absent':not bool(tools & write_names),
 'secret_values_recorded':False,
}
Path(sys.argv[3]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_RUNTIME
[ "$?" -eq 0 ] || fail_now "runtime_inspect_parse_failed" "INSPECT_PLUGIN_RUNTIME_JSON"
PLUGIN_ENABLED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["plugin_enabled"] else "NO")' "$TMP_ROOT/runtime-safe.json")"
PLUGIN_ERROR_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["plugin_error_count"])' "$TMP_ROOT/runtime-safe.json")"
RUNTIME_TOOL_COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["runtime_tools"]))' "$TMP_ROOT/runtime-safe.json")"
RUNTIME_HOOK_COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["runtime_hooks"]))' "$TMP_ROOT/runtime-safe.json")"
RUNTIME_TOOLS_MATCH="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["runtime_tools_match"] else "NO")' "$TMP_ROOT/runtime-safe.json")"
RUNTIME_HOOKS_MATCH="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["runtime_hooks_match"] else "NO")' "$TMP_ROOT/runtime-safe.json")"
WRITE_TOOLS_ABSENT="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["write_tools_absent"] else "NO")' "$TMP_ROOT/runtime-safe.json")"
[ "$PLUGIN_ENABLED" = "YES" ] || fail_now "plugin_not_enabled_after_install" "INSPECT_OPENCLAW_PLUGIN_CONFIG"
[ "$PLUGIN_ERROR_COUNT" = "0" ] || fail_now "plugin_error_after_install" "INSPECT_OPENCLAW_PLUGIN_RUNTIME"
[ "$RUNTIME_TOOLS_MATCH" = "YES" ] || fail_now "runtime_tool_contract_mismatch" "INSPECT_OPENCLAW_PLUGIN_RUNTIME"
[ "$RUNTIME_HOOKS_MATCH" = "YES" ] || fail_now "runtime_hook_contract_mismatch" "INSPECT_OPENCLAW_PLUGIN_RUNTIME"
[ "$WRITE_TOOLS_ABSENT" = "YES" ] || fail_now "unexpected_write_tool_registered" "ROLL_BACK_PLUGIN_INSTALL"

python3 - "$OPENCLAW_CONFIG" "$TMP_ROOT/config-after-safe.json" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<'PY_CONFIG_AFTER'
import hashlib,json,sys
from pathlib import Path
data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
names=sys.argv[3:6]
auth=data.get('gateway',{}).get('auth',{}) if isinstance(data.get('gateway'),dict) else {}
mode=auth.get('mode') or 'token'; secret=auth.get(mode)
if mode not in {'token','password'} or not isinstance(secret,str) or not secret: raise SystemExit(2)
tools=data.get('tools') if isinstance(data.get('tools'),dict) else {}
allow=tools.get('allow') if isinstance(tools.get('allow'),list) else []
deny=tools.get('deny') if isinstance(tools.get('deny'),list) else []
payload={
 'auth_mode':mode,
 'auth_secret_sha256':hashlib.sha256(secret.encode()).hexdigest(),
 'tools_allow_sha256':hashlib.sha256(json.dumps(allow,sort_keys=True).encode()).hexdigest(),
 'all_expected_denied':all(name in deny for name in names),
 'denied_tools':[name for name in names if name in deny],
 'secret_values_recorded':False,
}
Path(sys.argv[2]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_CONFIG_AFTER
[ "$?" -eq 0 ] || fail_now "postinstall_config_parse_failed" "INSPECT_OPENCLAW_CONFIG"
AUTH_SECRET_SHA_AFTER="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["auth_secret_sha256"])' "$TMP_ROOT/config-after-safe.json")"
AUTH_MODE_AFTER="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["auth_mode"])' "$TMP_ROOT/config-after-safe.json")"
TOOLS_ALLOW_SHA_AFTER="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tools_allow_sha256"])' "$TMP_ROOT/config-after-safe.json")"
TOOLS_EFFECTIVELY_DENIED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["all_expected_denied"] else "NO")' "$TMP_ROOT/config-after-safe.json")"
if [ "$AUTH_MODE" = "$AUTH_MODE_AFTER" ] && [ "$AUTH_SECRET_SHA_BEFORE" = "$AUTH_SECRET_SHA_AFTER" ]; then AUTH_SECRET_UNCHANGED="YES"; fi
[ "$AUTH_SECRET_UNCHANGED" = "YES" ] || fail_now "gateway_auth_changed_during_plugin_install" "ROLL_BACK_PLUGIN_INSTALL"
if [ "$TOOLS_ALLOW_SHA_BEFORE" = "$TOOLS_ALLOW_SHA_AFTER" ]; then TOOLS_ALLOW_UNCHANGED="YES"; fi
[ "$TOOLS_ALLOW_UNCHANGED" = "YES" ] || fail_now "tools_allow_changed_during_plugin_install" "ROLL_BACK_PLUGIN_INSTALL"
[ "$TOOLS_EFFECTIVELY_DENIED" = "YES" ] || fail_now "plugin_tools_not_explicitly_denied" "ROLL_BACK_PLUGIN_INSTALL"

ENQUEUE_LOOPBACK_ONLY="$(loopback_only "$ENQUEUE_PORT")"
INTAKE_LOOPBACK_ONLY="$(loopback_only "$INTAKE_PORT")"
[ "$ENQUEUE_LOOPBACK_ONLY" = "YES" ] || fail_now "enqueue_listener_not_loopback_only" "ROLL_BACK_PLUGIN_INSTALL"
[ "$INTAKE_LOOPBACK_ONLY" = "YES" ] || fail_now "intake_listener_not_loopback_only" "ROLL_BACK_PLUGIN_INSTALL"

QUEUE_AFTER="$(queue_fingerprint)"
[ "$QUEUE_BEFORE" = "$QUEUE_AFTER" ] && QUEUE_STATE_UNCHANGED="YES"
[ "$QUEUE_STATE_UNCHANGED" = "YES" ] || fail_now "queue_changed_during_plugin_install" "ROLL_BACK_PLUGIN_INSTALL"

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
if [ "$PRODUCT_HEAD_BEFORE" = "$PRODUCT_HEAD_AFTER" ] && [ "$PRODUCT_REMOTE_BEFORE" = "$PRODUCT_REMOTE_AFTER" ] && [ "$PRODUCT_STATUS_BEFORE" = "$PRODUCT_STATUS_AFTER" ] && [ "$PRODUCT_TREE_BEFORE" = "$PRODUCT_TREE_AFTER" ]; then PRODUCT_BASELINE_PRESERVED="YES"; fi
[ "$PRODUCT_BASELINE_PRESERVED" = "YES" ] || fail_now "product_baseline_changed_during_plugin_install" "ROLL_BACK_PLUGIN_INSTALL"

git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_AFTER_FILE" || fail_now "oris_status_recapture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_AFTER_SHA="$(sha256sum "$ORIS_STATUS_AFTER_FILE" | awk '{print $1}')"
[ "$ORIS_STATUS_BEFORE_SHA" = "$ORIS_STATUS_AFTER_SHA" ] && ORIS_WORKTREE_PRESERVED="YES"
[ "$ORIS_WORKTREE_PRESERVED" = "YES" ] || fail_now "oris_worktree_changed_during_plugin_install" "ROLL_BACK_PLUGIN_INSTALL"

python3 - "$MARKER_FILE" <<'PY_MARKER_DONE'
import json,os,sys
from pathlib import Path
path=Path(sys.argv[1]); data=json.loads(path.read_text(encoding='utf-8'))
data['state']='installed_tools_denied'
data['runtime_inspected']=True
data['rollback_script']='scripts/dev_employee_rollback_openclaw_native_plugin_20260618.sh'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
os.chmod(path,0o600)
PY_MARKER_DONE
[ "$?" -eq 0 ] || fail_now "private_install_marker_finalize_failed" "ROLL_BACK_PLUGIN_INSTALL"
MARKER_WRITTEN="YES"

RESULT="INSTALLED_TOOLS_DENIED"
NEXT_ACTION="RUN_CONTROLLED_READ_ONLY_TOOL_ENABLE_AND_BROWSER_SMOKE"

export TASK_ID STAMP RESULT FAILURE_CODE SOURCE_COMMIT VALIDATED_PLUGIN_TREE_MATCH OPENCLAW_VERSION NODE_VERSION NPM_VERSION NPM_INSTALL TSC_BUILD UNIT_TESTS MIXED_PLUGIN_VALIDATE NPM_PACK ARTIFACT_SHA256 CONFIG_BACKUP_CREATED TOOLS_DENY_APPLIED TOOLS_ALLOW_UNCHANGED AUTH_MODE AUTH_SECRET_UNCHANGED PLUGIN_INSTALL_RC PLUGIN_ENABLE_RC GATEWAY_RESTART GATEWAY_STATE DIRECT_ROOT_STATUS PUBLIC_ROOT_STATUS PUBLIC_ROOT_MATCHES_DIRECT PLUGIN_ENABLED PLUGIN_ERROR_COUNT RUNTIME_TOOL_COUNT RUNTIME_HOOK_COUNT RUNTIME_TOOLS_MATCH RUNTIME_HOOKS_MATCH WRITE_TOOLS_ABSENT TOOLS_EFFECTIVELY_DENIED ENQUEUE_LOOPBACK_ONLY INTAKE_LOOPBACK_ONLY QUEUE_STATE_UNCHANGED ORIS_WORKTREE_PRESERVED PRODUCT_BASELINE_PRESERVED MARKER_WRITTEN ROLLBACK_PERFORMED ROLLBACK_HEALTHY PRODUCT_TASK_SUBMITTED NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL BACKUP_FILE
python3 - "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path
payload={
 'task_id':os.environ['TASK_ID'],
 'checked_at':os.environ['STAMP'],
 'result':os.environ['RESULT'],
 'failure_code':os.environ.get('FAILURE_CODE') or None,
 'source':{
   'commit':os.environ['SOURCE_COMMIT'],
   'validated_plugin_tree_match':os.environ['VALIDATED_PLUGIN_TREE_MATCH']=='YES',
   'artifact_sha256':os.environ['ARTIFACT_SHA256'],
 },
 'build':{
   'npm_install':os.environ['NPM_INSTALL'],
   'typescript_build':os.environ['TSC_BUILD'],
   'unit_tests':os.environ['UNIT_TESTS'],
   'mixed_plugin_validate':os.environ['MIXED_PLUGIN_VALIDATE'],
   'npm_pack':os.environ['NPM_PACK'],
 },
 'config':{
   'backup_created':os.environ['CONFIG_BACKUP_CREATED']=='YES',
   'backup_file':os.environ['BACKUP_FILE'],
   'tools_deny_applied':os.environ['TOOLS_DENY_APPLIED']=='YES',
   'tools_allow_unchanged':os.environ['TOOLS_ALLOW_UNCHANGED']=='YES',
   'auth_mode':os.environ['AUTH_MODE'],
   'auth_secret_unchanged':os.environ['AUTH_SECRET_UNCHANGED']=='YES',
 },
 'runtime':{
   'plugin_install_rc':os.environ['PLUGIN_INSTALL_RC'],
   'plugin_enable_rc':os.environ['PLUGIN_ENABLE_RC'],
   'gateway_restart':os.environ['GATEWAY_RESTART'],
   'gateway_state':os.environ['GATEWAY_STATE'],
   'direct_root_status':os.environ['DIRECT_ROOT_STATUS'],
   'public_root_status':os.environ['PUBLIC_ROOT_STATUS'],
   'public_matches_direct':os.environ['PUBLIC_ROOT_MATCHES_DIRECT']=='YES',
   'plugin_enabled':os.environ['PLUGIN_ENABLED']=='YES',
   'plugin_error_count':int(os.environ['PLUGIN_ERROR_COUNT']),
   'runtime_tool_count':int(os.environ['RUNTIME_TOOL_COUNT']),
   'runtime_hook_count':int(os.environ['RUNTIME_HOOK_COUNT']),
   'runtime_tools_match':os.environ['RUNTIME_TOOLS_MATCH']=='YES',
   'runtime_hooks_match':os.environ['RUNTIME_HOOKS_MATCH']=='YES',
   'write_tools_absent':os.environ['WRITE_TOOLS_ABSENT']=='YES',
   'tools_effectively_denied':os.environ['TOOLS_EFFECTIVELY_DENIED']=='YES',
 },
 'safety':{
   'enqueue_loopback_only':os.environ['ENQUEUE_LOOPBACK_ONLY']=='YES',
   'intake_loopback_only':os.environ['INTAKE_LOOPBACK_ONLY']=='YES',
   'queue_state_unchanged':os.environ['QUEUE_STATE_UNCHANGED']=='YES',
   'oris_worktree_preserved':os.environ['ORIS_WORKTREE_PRESERVED']=='YES',
   'product_baseline_preserved':os.environ['PRODUCT_BASELINE_PRESERVED']=='YES',
   'marker_written':os.environ['MARKER_WRITTEN']=='YES',
   'rollback_performed':os.environ['ROLLBACK_PERFORMED'],
   'product_task_submitted':False,
   'openclaw_reinstalled_or_upgraded':False,
   'secret_values_recorded':False,
 },
 'next_action':os.environ['NEXT_ACTION'],
 'evidence':{
   'log_path':os.environ['EVIDENCE_LOG_REL'],
   'json_path':os.environ['EVIDENCE_JSON_REL'],
   'self_commit_sha_omitted_to_prevent_post_commit_log_drift':True,
 },
}
Path(sys.argv[1]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_RESULT

{
  echo "checked_at=$(date -Is)"
  echo "task_id=$TASK_ID"
  echo "result=$RESULT"
  echo "source_commit=$SOURCE_COMMIT"
  echo "validated_plugin_tree_match=$VALIDATED_PLUGIN_TREE_MATCH"
  echo "artifact_sha256=$ARTIFACT_SHA256"
  echo "npm_install=$NPM_INSTALL"
  echo "typescript_build=$TSC_BUILD"
  echo "unit_tests=$UNIT_TESTS"
  echo "mixed_plugin_validate=$MIXED_PLUGIN_VALIDATE"
  echo "npm_pack=$NPM_PACK"
  echo "tools_deny_applied=$TOOLS_DENY_APPLIED"
  echo "tools_allow_unchanged=$TOOLS_ALLOW_UNCHANGED"
  echo "auth_mode=$AUTH_MODE"
  echo "auth_secret_unchanged=$AUTH_SECRET_UNCHANGED"
  echo "plugin_enabled=$PLUGIN_ENABLED"
  echo "plugin_error_count=$PLUGIN_ERROR_COUNT"
  echo "runtime_tool_count=$RUNTIME_TOOL_COUNT"
  echo "runtime_hook_count=$RUNTIME_HOOK_COUNT"
  echo "runtime_tools_match=$RUNTIME_TOOLS_MATCH"
  echo "runtime_hooks_match=$RUNTIME_HOOKS_MATCH"
  echo "write_tools_absent=$WRITE_TOOLS_ABSENT"
  echo "tools_effectively_denied=$TOOLS_EFFECTIVELY_DENIED"
  echo "queue_state_unchanged=$QUEUE_STATE_UNCHANGED"
  echo "oris_worktree_preserved=$ORIS_WORKTREE_PRESERVED"
  echo "product_baseline_preserved=$PRODUCT_BASELINE_PRESERVED"
  echo "product_task_submitted=NO"
  echo "secret_values_recorded=NO"
} >> "$RUN_LOG"

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY_SCAN'
import re,sys
from pathlib import Path
patterns=[
 re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
 re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),
 re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),
 re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
 re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b')
]
for filename in sys.argv[1:]:
    text=Path(filename).read_text(encoding='utf-8',errors='replace')
    if any(pattern.search(text) for pattern in patterns): raise SystemExit(1)
PY_SCAN
if [ "$?" -eq 0 ]; then SECRET_SCAN="PASS"; else fail_now "install_evidence_secret_scan_failed" "ROLL_BACK_PLUGIN_INSTALL"; fi

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "evidence_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL" || fail_now "evidence_directory_create_failed" "CHECK_EVIDENCE_WORKTREE_PERMISSIONS"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_COPY'
import json,sys
from pathlib import Path
sl,dl,sj,dj=map(Path,sys.argv[1:])
dl.write_text('\n'.join(line.rstrip(' \t\r') for line in sl.read_text(encoding='utf-8',errors='replace').splitlines())+'\n',encoding='utf-8')
dj.write_text(json.dumps(json.loads(sj.read_text(encoding='utf-8')),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_COPY
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native plugin install with tools denied $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then EVIDENCE_REMOTE_VERIFIED="YES"; else fail_now "evidence_remote_sha_mismatch" "VERIFY_ORIS_REMOTE_MAIN"; fi

summary
exit 0
