#!/usr/bin/env bash

TASK_ID="commercial-openclaw-native-plugin-validation-20260618"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
PLUGIN_REL="orchestration/openclaw_plugins/oris-dev-employee"
PLUGIN_SOURCE="$ORIS_REPO/$PLUGIN_REL"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_SERVICE="openclaw-gateway.service"
EXPECTED_OPENCLAW_VERSION="2026.5.19"
EXPECTED_PRODUCT_COMMIT="bcb93e17ea88704548101f5e4a5c460e15a80ec7"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-plugin-validation-${STAMP}-XXXXXX)"
BUILD_ROOT="$TMP_ROOT/plugin"
RUN_LOG="$TMP_ROOT/validation.log"
RESULT_JSON="$TMP_ROOT/validation.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_native_plugin_validation"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/openclaw-native-plugin-validation-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/openclaw-native-plugin-validation-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
VALIDATION_COMPLETE="NO"
OPENCLAW_VERSION="unknown"
NODE_VERSION="unknown"
NPM_VERSION="unknown"
OPENCLAW_PACKAGE_ROOT=""
NPM_INSTALL="NOT_RUN"
TSC_BUILD="NOT_RUN"
UNIT_TESTS="NOT_RUN"
PLUGIN_VALIDATE="NOT_RUN"
MANIFEST_CONTRACT="NOT_RUN"
RUNTIME_IMPORT="NOT_RUN"
STATIC_SAFETY_GATE="NOT_RUN"
LOOPBACK_API_HEALTH="unknown"
LOOPBACK_QUEUE_STATUS="000"
LOOPBACK_LATEST_STATUS="000"
PLUGIN_PRESENT_BEFORE="unknown"
PLUGIN_PRESENT_AFTER="unknown"
QUEUE_STATE_UNCHANGED="NO"
OPENCLAW_CONFIG_UNCHANGED="NO"
OPENCLAW_SERVICE_PID_UNCHANGED="NO"
PRODUCT_BASELINE_PRESERVED="NO"
ORIS_MAIN_WORKTREE_UNCHANGED="NO"
PRODUCT_TASK_SUBMITTED="NO"
PLUGIN_INSTALLED_OR_ENABLED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_NATIVE_PLUGIN_VALIDATION_FAILURE"

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
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "VALIDATION_COMPLETE=$VALIDATION_COMPLETE"
  echo "OPENCLAW_VERSION=$OPENCLAW_VERSION"
  echo "NODE_VERSION=$NODE_VERSION"
  echo "NPM_VERSION=$NPM_VERSION"
  echo "NPM_INSTALL=$NPM_INSTALL"
  echo "TSC_BUILD=$TSC_BUILD"
  echo "UNIT_TESTS=$UNIT_TESTS"
  echo "PLUGIN_VALIDATE=$PLUGIN_VALIDATE"
  echo "MANIFEST_CONTRACT=$MANIFEST_CONTRACT"
  echo "RUNTIME_IMPORT=$RUNTIME_IMPORT"
  echo "STATIC_SAFETY_GATE=$STATIC_SAFETY_GATE"
  echo "LOOPBACK_API_HEALTH=$LOOPBACK_API_HEALTH"
  echo "LOOPBACK_QUEUE_STATUS=$LOOPBACK_QUEUE_STATUS"
  echo "LOOPBACK_LATEST_STATUS=$LOOPBACK_LATEST_STATUS"
  echo "PLUGIN_PRESENT_BEFORE=$PLUGIN_PRESENT_BEFORE"
  echo "PLUGIN_PRESENT_AFTER=$PLUGIN_PRESENT_AFTER"
  echo "QUEUE_STATE_UNCHANGED=$QUEUE_STATE_UNCHANGED"
  echo "OPENCLAW_CONFIG_UNCHANGED=$OPENCLAW_CONFIG_UNCHANGED"
  echo "OPENCLAW_SERVICE_PID_UNCHANGED=$OPENCLAW_SERVICE_PID_UNCHANGED"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "ORIS_MAIN_WORKTREE_UNCHANGED=$ORIS_MAIN_WORKTREE_UNCHANGED"
  echo "PRODUCT_TASK_SUBMITTED=$PRODUCT_TASK_SUBMITTED"
  echo "PLUGIN_INSTALLED_OR_ENABLED=$PLUGIN_INSTALLED_OR_ENABLED"
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

queue_fingerprint() {
  python3 - "$ORIS_REPO/orchestration/dev_employee_queue" <<'PY_QUEUE'
import hashlib
import sys
from pathlib import Path
root=Path(sys.argv[1])
rows=[]
if root.exists():
    for path in sorted(root.glob('*.json')):
        try:
            stat=path.stat()
            rows.append(f"{path.name}\t{stat.st_size}\t{stat.st_mtime_ns}")
        except FileNotFoundError:
            pass
print(hashlib.sha256('\n'.join(rows).encode()).hexdigest())
PY_QUEUE
}

plugin_present() {
  local target="$1"
  python3 - "$target" <<'PY_PLUGIN_PRESENT'
import json
import sys
from pathlib import Path
path=Path(sys.argv[1])
try:
    data=json.loads(path.read_text(encoding='utf-8'))
except Exception:
    print('unknown')
    raise SystemExit(0)
plugins=data.get('plugins') if isinstance(data,dict) else None
entries=plugins.get('plugins') if isinstance(plugins,dict) and isinstance(plugins.get('plugins'),list) else plugins.get('entries') if isinstance(plugins,dict) else None
found=False
if isinstance(entries,dict):
    found='oris-dev-employee' in entries
elif isinstance(entries,list):
    found=any((isinstance(x,str) and x=='oris-dev-employee') or (isinstance(x,dict) and (x.get('id')=='oris-dev-employee' or x.get('name')=='oris-dev-employee')) for x in entries)
print('YES' if found else 'NO')
PY_PLUGIN_PRESENT
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user" "RUN_AS_ADMIN"; fi
for cmd in git curl python3 sha256sum systemctl node npm openclaw cp find grep awk ln; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -d "$PLUGIN_SOURCE" ] || fail_now "plugin_source_missing" "PULL_ORIS_MAIN_AND_RETRY"
[ -f "$OPENCLAW_CONFIG" ] || fail_now "openclaw_config_missing" "RESTORE_OPENCLAW_CONFIG"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=ISOLATED_BUILD_TEST_VALIDATE_ONLY"
log "PLUGIN_SOURCE=$PLUGIN_REL"
log "PLUGIN_INSTALLED_OR_ENABLED=NO"
log "PRODUCT_TASK_SUBMITTED=NO"
log "OPENCLAW_CONFIG_MUTATED=NO"
log "OPENCLAW_SERVICE_RESTARTED=NO"
log "PRODUCT_REPOSITORY_MUTATED=NO"
log "SECRET_VALUES_RECORDED=NO"

OPENCLAW_VERSION="$(openclaw --version 2>/dev/null | head -n 1 | tr -d '\r')"
NODE_VERSION="$(node --version 2>/dev/null || true)"
NPM_VERSION="$(npm --version 2>/dev/null || true)"
case "$OPENCLAW_VERSION" in *"$EXPECTED_OPENCLAW_VERSION"*) ;; *) fail_now "unexpected_openclaw_version" "REVIEW_PLUGIN_COMPATIBILITY" ;; esac

OPENCLAW_BIN="$(command -v openclaw)"
OPENCLAW_PACKAGE_ROOT="$(python3 - "$OPENCLAW_BIN" <<'PY_OPENCLAW_ROOT'
import json
import sys
from pathlib import Path
start=Path(sys.argv[1]).resolve()
for parent in [start.parent,*start.parents]:
    package=parent/'package.json'
    if not package.is_file():
        continue
    try:
        data=json.loads(package.read_text(encoding='utf-8'))
    except Exception:
        continue
    if data.get('name')=='openclaw':
        print(parent)
        raise SystemExit(0)
raise SystemExit(1)
PY_OPENCLAW_ROOT
)"
[ -n "$OPENCLAW_PACKAGE_ROOT" ] && [ -f "$OPENCLAW_PACKAGE_ROOT/package.json" ] || fail_now "openclaw_package_root_not_found" "INSPECT_EXISTING_OPENCLAW_INSTALLATION"
log "OPENCLAW_PACKAGE_ROOT=$OPENCLAW_PACKAGE_ROOT"

OPENCLAW_CONFIG_HASH_BEFORE="$(sha256sum "$OPENCLAW_CONFIG" | awk '{print $1}')"
OPENCLAW_PID_BEFORE="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"
ORIS_HEAD_BEFORE="$(git -C "$ORIS_REPO" rev-parse HEAD 2>/dev/null || true)"
ORIS_STATUS_BEFORE="$(git -C "$ORIS_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
QUEUE_FINGERPRINT_BEFORE="$(queue_fingerprint)"
PLUGIN_PRESENT_BEFORE="$(plugin_present "$OPENCLAW_CONFIG")"

[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_head" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_COMMIT" ] || fail_now "unexpected_product_remote_main" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ -z "$PRODUCT_STATUS_BEFORE" ] || fail_now "product_worktree_not_clean" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ -z "$ORIS_STATUS_BEFORE" ] || fail_now "oris_main_worktree_not_clean_before_validation" "PRESERVE_ORIS_MAIN_WORKTREE_BEFORE_VALIDATION"
[ "$PLUGIN_PRESENT_BEFORE" = "NO" ] || fail_now "plugin_already_present_before_validation" "INSPECT_EXISTING_OPENCLAW_PLUGIN_STATE"

cp -a "$PLUGIN_SOURCE/." "$BUILD_ROOT/" || fail_now "plugin_temp_copy_failed" "CHECK_TEMP_DIRECTORY_PERMISSIONS"

if (cd "$BUILD_ROOT" && npm install --ignore-scripts --no-audit --no-fund --legacy-peer-deps) >> "$RUN_LOG" 2>&1; then
  NPM_INSTALL="PASS"
else
  NPM_INSTALL="FAIL"
  fail_now "plugin_dependency_install_failed" "INSPECT_NATIVE_PLUGIN_VALIDATION_LOG"
fi

rm -rf "$BUILD_ROOT/node_modules/openclaw"
ln -s "$OPENCLAW_PACKAGE_ROOT" "$BUILD_ROOT/node_modules/openclaw" || fail_now "openclaw_sdk_link_failed" "INSPECT_EXISTING_OPENCLAW_PACKAGE"

if (cd "$BUILD_ROOT" && npm run build) >> "$RUN_LOG" 2>&1; then
  TSC_BUILD="PASS"
else
  TSC_BUILD="FAIL"
  fail_now "plugin_typescript_build_failed" "REPAIR_PLUGIN_SOURCE_FROM_VALIDATION_LOG"
fi

if (cd "$BUILD_ROOT" && npm test) >> "$RUN_LOG" 2>&1; then
  UNIT_TESTS="PASS"
else
  UNIT_TESTS="FAIL"
  fail_now "plugin_unit_tests_failed" "REPAIR_PLUGIN_TEST_OR_SOURCE"
fi

if (cd "$BUILD_ROOT" && openclaw plugins validate --root . --entry ./dist/index.js) >> "$RUN_LOG" 2>&1; then
  PLUGIN_VALIDATE="PASS"
else
  PLUGIN_VALIDATE="FAIL"
  fail_now "openclaw_plugin_validate_failed" "REPAIR_PLUGIN_MANIFEST_OR_ENTRY"
fi

if (cd "$BUILD_ROOT" && node --input-type=module - <<'JS_RUNTIME'
const moduleValue = await import('./dist/index.js');
if (!moduleValue.default || typeof moduleValue.default !== 'object') {
  throw new Error('default plugin entry is missing');
}
const id = moduleValue.default.id ?? moduleValue.default.plugin?.id;
if (id !== 'oris-dev-employee') {
  throw new Error(`unexpected plugin id: ${String(id)}`);
}
JS_RUNTIME
) >> "$RUN_LOG" 2>&1; then
  RUNTIME_IMPORT="PASS"
else
  RUNTIME_IMPORT="FAIL"
  fail_now "plugin_runtime_import_failed" "REPAIR_PLUGIN_ENTRY"
fi

python3 - "$BUILD_ROOT/openclaw.plugin.json" "$BUILD_ROOT/package.json" "$BUILD_ROOT/dist/index.js" <<'PY_MANIFEST'
import json
import re
import sys
from pathlib import Path
manifest=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
package=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
entry=Path(sys.argv[3]).read_text(encoding='utf-8',errors='replace')
expected=['oris_queue_status','oris_task_status','oris_latest_task_status']
if manifest.get('id')!='oris-dev-employee':
    raise SystemExit('unexpected manifest id')
if manifest.get('contracts',{}).get('tools')!=expected:
    raise SystemExit('unexpected tool contract')
metadata=manifest.get('toolMetadata',{})
if any(metadata.get(name,{}).get('optional') is not True for name in expected):
    raise SystemExit('all tools must be optional')
extensions=package.get('openclaw',{}).get('extensions')
if extensions!=['./dist/index.js']:
    raise SystemExit('unexpected package extension entry')
for name in expected:
    if name not in entry:
        raise SystemExit(f'missing runtime tool name: {name}')
for hook in ['model_call_ended','after_tool_call','agent_end']:
    if hook not in entry:
        raise SystemExit(f'missing telemetry hook: {hook}')
PY_MANIFEST
if [ "$?" -eq 0 ]; then
  MANIFEST_CONTRACT="PASS"
else
  MANIFEST_CONTRACT="FAIL"
  fail_now "plugin_manifest_contract_failed" "REPAIR_PLUGIN_MANIFEST_AND_RUNTIME_ALIGNMENT"
fi

python3 - "$BUILD_ROOT/src/index.ts" "$BUILD_ROOT/openclaw.plugin.json" <<'PY_STATIC_SAFETY'
import json
import re
import sys
from pathlib import Path
source=Path(sys.argv[1]).read_text(encoding='utf-8')
manifest=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
for forbidden in ['oris_submit_task','oris_cancel_task','oris_retry_task']:
    if forbidden in source or forbidden in json.dumps(manifest):
        raise SystemExit(f'forbidden side-effect tool present: {forbidden}')
if re.search(r'method\s*:\s*["\'](?:POST|PUT|PATCH|DELETE)["\']',source,re.I):
    raise SystemExit('side-effecting HTTP method present')
if 'optional: true' not in source:
    raise SystemExit('runtime tools are not optional')
for secret_word in ['gateway token','authorization: bearer','api_key=', 'password=']:
    if secret_word.lower() in source.lower():
        raise SystemExit('hard-coded credential marker found')
if 'prompt' in source.lower() and 'FORBIDDEN_KEY_RE' not in source:
    raise SystemExit('prompt redaction guard missing')
PY_STATIC_SAFETY
if [ "$?" -eq 0 ]; then
  STATIC_SAFETY_GATE="PASS"
else
  STATIC_SAFETY_GATE="FAIL"
  fail_now "plugin_static_safety_gate_failed" "REPAIR_PLUGIN_SECURITY_BOUNDARY"
fi

LOOPBACK_API_HEALTH="$(curl -sS --max-time 8 http://127.0.0.1:18891/health 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print("YES" if d.get("status")=="ok" else "NO")' 2>/dev/null || echo NO)"
LOOPBACK_QUEUE_STATUS="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:18891/queue 2>/dev/null || true)"
LOOPBACK_LATEST_STATUS="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:18891/latest 2>/dev/null || true)"
[ "$LOOPBACK_API_HEALTH" = "YES" ] || fail_now "loopback_oris_status_api_unhealthy" "RESTORE_ORIS_ENQUEUE_STATUS_SERVICE"
[ "$LOOPBACK_QUEUE_STATUS" = "200" ] || fail_now "loopback_queue_status_unhealthy" "RESTORE_ORIS_ENQUEUE_STATUS_SERVICE"
[ "$LOOPBACK_LATEST_STATUS" = "200" ] || fail_now "loopback_latest_status_unhealthy" "RESTORE_ORIS_ENQUEUE_STATUS_SERVICE"

OPENCLAW_CONFIG_HASH_AFTER="$(sha256sum "$OPENCLAW_CONFIG" | awk '{print $1}')"
OPENCLAW_PID_AFTER="$(systemctl --user show "$OPENCLAW_SERVICE" -p MainPID --value 2>/dev/null || true)"
ORIS_HEAD_AFTER="$(git -C "$ORIS_REPO" rev-parse HEAD 2>/dev/null || true)"
ORIS_STATUS_AFTER="$(git -C "$ORIS_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_TREE_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
QUEUE_FINGERPRINT_AFTER="$(queue_fingerprint)"
PLUGIN_PRESENT_AFTER="$(plugin_present "$OPENCLAW_CONFIG")"

[ "$OPENCLAW_CONFIG_HASH_BEFORE" = "$OPENCLAW_CONFIG_HASH_AFTER" ] && OPENCLAW_CONFIG_UNCHANGED="YES"
[ "$OPENCLAW_PID_BEFORE" = "$OPENCLAW_PID_AFTER" ] && OPENCLAW_SERVICE_PID_UNCHANGED="YES"
[ "$QUEUE_FINGERPRINT_BEFORE" = "$QUEUE_FINGERPRINT_AFTER" ] && QUEUE_STATE_UNCHANGED="YES"
[ "$ORIS_HEAD_BEFORE" = "$ORIS_HEAD_AFTER" ] && [ "$ORIS_STATUS_BEFORE" = "$ORIS_STATUS_AFTER" ] && ORIS_MAIN_WORKTREE_UNCHANGED="YES"
if [ "$PRODUCT_HEAD_BEFORE" = "$PRODUCT_HEAD_AFTER" ] && [ "$PRODUCT_REMOTE_BEFORE" = "$PRODUCT_REMOTE_AFTER" ] && [ "$PRODUCT_STATUS_BEFORE" = "$PRODUCT_STATUS_AFTER" ] && [ "$PRODUCT_TREE_BEFORE" = "$PRODUCT_TREE_AFTER" ]; then PRODUCT_BASELINE_PRESERVED="YES"; fi

[ "$OPENCLAW_CONFIG_UNCHANGED" = "YES" ] || fail_now "openclaw_config_changed_during_validation" "INSPECT_UNEXPECTED_PLUGIN_INSTALLATION"
[ "$OPENCLAW_SERVICE_PID_UNCHANGED" = "YES" ] || fail_now "openclaw_service_restarted_during_validation" "INSPECT_UNEXPECTED_RUNTIME_CHANGE"
[ "$QUEUE_STATE_UNCHANGED" = "YES" ] || fail_now "queue_state_changed_during_validation" "INSPECT_UNEXPECTED_TASK_SUBMISSION"
[ "$ORIS_MAIN_WORKTREE_UNCHANGED" = "YES" ] || fail_now "oris_main_worktree_changed_during_validation" "INSPECT_UNEXPECTED_ORIS_MUTATION"
[ "$PRODUCT_BASELINE_PRESERVED" = "YES" ] || fail_now "product_baseline_changed_during_validation" "RESTORE_COMPLETED_PRODUCT_BASELINE"
[ "$PLUGIN_PRESENT_AFTER" = "NO" ] || fail_now "plugin_became_configured_during_validation" "REMOVE_UNEXPECTED_PLUGIN_CONFIGURATION"

VALIDATION_COMPLETE="YES"
RESULT="VALIDATED_NOT_INSTALLED"
NEXT_ACTION="DESIGN_REVERSIBLE_PLUGIN_INSTALL_WITH_TOOLS_DISABLED_THEN_RUNTIME_INSPECT"

export TASK_ID STAMP RESULT FAILURE_CODE VALIDATION_COMPLETE OPENCLAW_VERSION NODE_VERSION NPM_VERSION OPENCLAW_PACKAGE_ROOT NPM_INSTALL TSC_BUILD UNIT_TESTS PLUGIN_VALIDATE MANIFEST_CONTRACT RUNTIME_IMPORT STATIC_SAFETY_GATE LOOPBACK_API_HEALTH LOOPBACK_QUEUE_STATUS LOOPBACK_LATEST_STATUS PLUGIN_PRESENT_BEFORE PLUGIN_PRESENT_AFTER QUEUE_STATE_UNCHANGED OPENCLAW_CONFIG_UNCHANGED OPENCLAW_SERVICE_PID_UNCHANGED PRODUCT_BASELINE_PRESERVED ORIS_MAIN_WORKTREE_UNCHANGED PRODUCT_TASK_SUBMITTED PLUGIN_INSTALLED_OR_ENABLED NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$BUILD_ROOT/openclaw.plugin.json" "$BUILD_ROOT/package.json" "$RESULT_JSON" <<'PY_RESULT'
import hashlib
import json
import os
import sys
from pathlib import Path
manifest_path=Path(sys.argv[1]); package_path=Path(sys.argv[2]); out=Path(sys.argv[3])
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
package=json.loads(package_path.read_text(encoding='utf-8'))
payload={
  'task_id':os.environ['TASK_ID'],
  'checked_at':os.environ['STAMP'],
  'result':os.environ['RESULT'],
  'failure_code':os.environ.get('FAILURE_CODE') or None,
  'runtime':{
    'openclaw_version':os.environ['OPENCLAW_VERSION'],
    'node_version':os.environ['NODE_VERSION'],
    'npm_version':os.environ['NPM_VERSION'],
    'existing_openclaw_package_root':os.environ['OPENCLAW_PACKAGE_ROOT'],
  },
  'validation':{
    'npm_install':os.environ['NPM_INSTALL'],
    'typescript_build':os.environ['TSC_BUILD'],
    'unit_tests':os.environ['UNIT_TESTS'],
    'openclaw_plugin_validate':os.environ['PLUGIN_VALIDATE'],
    'manifest_contract':os.environ['MANIFEST_CONTRACT'],
    'runtime_import':os.environ['RUNTIME_IMPORT'],
    'static_safety_gate':os.environ['STATIC_SAFETY_GATE'],
    'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    'package_sha256':hashlib.sha256(package_path.read_bytes()).hexdigest(),
    'plugin_id':manifest.get('id'),
    'tool_contract':manifest.get('contracts',{}).get('tools',[]),
    'optional_tools':sorted(name for name,value in manifest.get('toolMetadata',{}).items() if isinstance(value,dict) and value.get('optional') is True),
    'package_version':package.get('version'),
  },
  'loopback_api':{
    'health_ok':os.environ['LOOPBACK_API_HEALTH']=='YES',
    'queue_status':os.environ['LOOPBACK_QUEUE_STATUS'],
    'latest_status':os.environ['LOOPBACK_LATEST_STATUS'],
  },
  'safety':{
    'plugin_present_before':os.environ['PLUGIN_PRESENT_BEFORE'],
    'plugin_present_after':os.environ['PLUGIN_PRESENT_AFTER'],
    'queue_state_unchanged':os.environ['QUEUE_STATE_UNCHANGED']=='YES',
    'openclaw_config_unchanged':os.environ['OPENCLAW_CONFIG_UNCHANGED']=='YES',
    'openclaw_service_pid_unchanged':os.environ['OPENCLAW_SERVICE_PID_UNCHANGED']=='YES',
    'product_baseline_preserved':os.environ['PRODUCT_BASELINE_PRESERVED']=='YES',
    'oris_main_worktree_unchanged':os.environ['ORIS_MAIN_WORKTREE_UNCHANGED']=='YES',
    'product_task_submitted':False,
    'plugin_installed_or_enabled':False,
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
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_RESULT

{
  echo "OPENCLAW_VERSION=$OPENCLAW_VERSION"
  echo "NODE_VERSION=$NODE_VERSION"
  echo "NPM_VERSION=$NPM_VERSION"
  echo "NPM_INSTALL=$NPM_INSTALL"
  echo "TSC_BUILD=$TSC_BUILD"
  echo "UNIT_TESTS=$UNIT_TESTS"
  echo "PLUGIN_VALIDATE=$PLUGIN_VALIDATE"
  echo "MANIFEST_CONTRACT=$MANIFEST_CONTRACT"
  echo "RUNTIME_IMPORT=$RUNTIME_IMPORT"
  echo "STATIC_SAFETY_GATE=$STATIC_SAFETY_GATE"
  echo "PLUGIN_INSTALLED_OR_ENABLED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "SECRET_VALUES_RECORDED=NO"
} >> "$RUN_LOG"

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY_SECRET_SCAN'
import re
import sys
from pathlib import Path
patterns=[
 re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
 re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),
 re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),
 re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
 re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
 re.compile(r'(?i)(password|authorization|credential|gateway[_ -]?token|api[_ -]?key|secret)(\s*[=:]\s*|\s+)(?!<redacted>|true\b|false\b|yes\b|no\b|null\b|values\b|recorded\b)[A-Za-z0-9._~+/-]{16,}'),
]
for filename in sys.argv[1:]:
    text=Path(filename).read_text(encoding='utf-8',errors='replace')
    if any(pattern.search(text) for pattern in patterns):
        raise SystemExit(1)
PY_SECRET_SCAN
if [ "$?" -eq 0 ]; then SECRET_SCAN="PASS"; else fail_now "validation_evidence_secret_scan_failed" "REPAIR_VALIDATION_EVIDENCE_REDACTION"; fi

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL" || fail_now "evidence_directory_create_failed" "CHECK_EVIDENCE_WORKTREE_PERMISSIONS"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_NORMALIZE'
import json
import sys
from pathlib import Path
sl,dl,sj,dj=map(Path,sys.argv[1:])
dl.write_text('\n'.join(line.rstrip(' \t\r') for line in sl.read_text(encoding='utf-8',errors='replace').splitlines())+'\n',encoding='utf-8')
dj.write_text(json.dumps(json.loads(sj.read_text(encoding='utf-8')),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY_NORMALIZE
[ "$?" -eq 0 ] || fail_now "evidence_normalization_failed" "INSPECT_VALIDATION_EVIDENCE"
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native OpenClaw plugin validation $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
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
