#!/usr/bin/env bash

TASK_ID="commercial-openclaw-native-plugin-validation-20260618"
ORIS_REPO="/home/admin/projects/oris"
PLUGIN_REL="orchestration/openclaw_plugins/oris-dev-employee"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-plugin-ts-diagnostic-${STAMP}-XXXXXX)"
ARCHIVE_ROOT="$TMP_ROOT/archive"
BUILD_ROOT="$ARCHIVE_ROOT/$PLUGIN_REL"
RAW_LOG="$TMP_ROOT/tsc.raw.log"
SAFE_LOG="$TMP_ROOT/tsc.safe.log"
RESULT_JSON="$TMP_ROOT/result.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_native_plugin_validation"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/openclaw-native-plugin-ts-diagnostic-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/openclaw-native-plugin-ts-diagnostic-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
SOURCE_REF="origin/main"
SOURCE_COMMIT=""
OPENCLAW_VERSION="unknown"
NODE_VERSION="unknown"
NPM_VERSION="unknown"
NPM_INSTALL="NOT_RUN"
TSC_RC="not_run"
TSC_ERROR_COUNT="unknown"
TSC_ERROR_CODES=""
TSC_ERROR_FILES=""
WORKTREE_PRESERVED="NO"
CONFIG_CHANGED="unknown"
SERVICE_PID_CHANGED="unknown"
QUEUE_CHANGED="unknown"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="READ_TYPESCRIPT_DIAGNOSTIC_EVIDENCE_AND_PATCH_PLUGIN_SOURCE"

umask 077
mkdir -p "$ARCHIVE_ROOT"
: > "$RAW_LOG"
: > "$SAFE_LOG"

cleanup() {
  if [ -d "$WORKTREE" ]; then
    git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "SOURCE_REF=$SOURCE_REF"
  echo "SOURCE_COMMIT=$SOURCE_COMMIT"
  echo "OPENCLAW_VERSION=$OPENCLAW_VERSION"
  echo "NODE_VERSION=$NODE_VERSION"
  echo "NPM_VERSION=$NPM_VERSION"
  echo "NPM_INSTALL=$NPM_INSTALL"
  echo "TSC_RC=$TSC_RC"
  echo "TSC_ERROR_COUNT=$TSC_ERROR_COUNT"
  echo "TSC_ERROR_CODES=$TSC_ERROR_CODES"
  echo "TSC_ERROR_FILES=$TSC_ERROR_FILES"
  echo "WORKTREE_PRESERVED=$WORKTREE_PRESERVED"
  echo "CONFIG_CHANGED=$CONFIG_CHANGED"
  echo "SERVICE_PID_CHANGED=$SERVICE_PID_CHANGED"
  echo "QUEUE_CHANGED=$QUEUE_CHANGED"
  echo "SECRET_SCAN=$SECRET_SCAN"
  echo "PLUGIN_INSTALLED_OR_ENABLED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
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
  RESULT="FAILED"
  summary
  exit 1
}

fingerprint_queue() {
  python3 - "$ORIS_REPO/orchestration/dev_employee_queue" <<'PY'
import hashlib,sys
from pathlib import Path
root=Path(sys.argv[1]); rows=[]
if root.exists():
    for p in sorted(root.glob('*.json')):
        try:
            s=p.stat(); rows.append(f"{p.name}\t{s.st_size}\t{s.st_mtime_ns}")
        except FileNotFoundError:
            pass
print(hashlib.sha256('\n'.join(rows).encode()).hexdigest())
PY
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user"; fi
for cmd in git tar npm node openclaw python3 sha256sum systemctl; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd"
done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing"

git -C "$ORIS_REPO" fetch origin main >/dev/null 2>&1 || fail_now "oris_fetch_failed"
SOURCE_COMMIT="$(git -C "$ORIS_REPO" rev-parse origin/main 2>/dev/null || true)"
[ -n "$SOURCE_COMMIT" ] || fail_now "origin_main_unresolved"

STATUS_BEFORE="$TMP_ROOT/status-before.bin"
STATUS_AFTER="$TMP_ROOT/status-after.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$STATUS_BEFORE" || fail_now "status_before_failed"
STATUS_BEFORE_SHA="$(sha256sum "$STATUS_BEFORE" | awk '{print $1}')"
CONFIG_FILE="$HOME/.openclaw/openclaw.json"
CONFIG_SHA_BEFORE="$(sha256sum "$CONFIG_FILE" 2>/dev/null | awk '{print $1}')"
PID_BEFORE="$(systemctl --user show openclaw-gateway.service -p MainPID --value 2>/dev/null || true)"
QUEUE_BEFORE="$(fingerprint_queue)"

OPENCLAW_VERSION="$(openclaw --version 2>/dev/null | head -n 1 | tr -d '\r')"
NODE_VERSION="$(node --version 2>/dev/null || true)"
NPM_VERSION="$(npm --version 2>/dev/null || true)"

OPENCLAW_BIN="$(command -v openclaw)"
OPENCLAW_PACKAGE_ROOT="$(python3 - "$OPENCLAW_BIN" <<'PY'
import json,sys
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
PY
)"
[ -n "$OPENCLAW_PACKAGE_ROOT" ] || fail_now "openclaw_package_root_not_found"

if ! git -C "$ORIS_REPO" archive origin/main "$PLUGIN_REL" | tar -x -C "$ARCHIVE_ROOT"; then
  fail_now "plugin_archive_failed"
fi
[ -f "$BUILD_ROOT/package.json" ] || fail_now "plugin_package_missing_in_archive"

if (cd "$BUILD_ROOT" && npm install --ignore-scripts --no-audit --no-fund --legacy-peer-deps) > "$TMP_ROOT/npm.log" 2>&1; then
  NPM_INSTALL="PASS"
else
  NPM_INSTALL="FAIL"
  cp "$TMP_ROOT/npm.log" "$RAW_LOG"
  TSC_RC="not_run"
fi

if [ "$NPM_INSTALL" = "PASS" ]; then
  rm -rf "$BUILD_ROOT/node_modules/openclaw"
  ln -s "$OPENCLAW_PACKAGE_ROOT" "$BUILD_ROOT/node_modules/openclaw" || fail_now "openclaw_sdk_link_failed"
  (cd "$BUILD_ROOT" && ./node_modules/.bin/tsc -p tsconfig.json --pretty false) > "$RAW_LOG" 2>&1
  TSC_RC="$?"
fi

python3 - "$RAW_LOG" "$SAFE_LOG" "$BUILD_ROOT" "$OPENCLAW_PACKAGE_ROOT" <<'PY'
import re,sys
from pathlib import Path
raw=Path(sys.argv[1]).read_text(encoding='utf-8',errors='replace')
build=sys.argv[3]
openclaw=sys.argv[4]
text=raw.replace(build,'<plugin-build>').replace(openclaw,'<openclaw-package>')
text=re.sub(r'/home/[^\s:()]+','<redacted-home-path>',text)
text=re.sub(r'/tmp/[^\s:()]+','<redacted-tmp-path>',text)
text=re.sub(r'(?i)(token|password|secret|authorization|api[_-]?key)(\s*[=:]\s*)([^\s]+)',r'\1\2<redacted>',text)
Path(sys.argv[2]).write_text(text.rstrip()+"\n",encoding='utf-8')
PY

TSC_ERROR_COUNT="$(grep -Eoc 'error TS[0-9]+' "$SAFE_LOG" 2>/dev/null || true)"
TSC_ERROR_CODES="$(grep -Eo 'TS[0-9]+' "$SAFE_LOG" 2>/dev/null | sort -u | paste -sd, -)"
TSC_ERROR_FILES="$(grep -Eo '(^|[[:space:]])(src/[^(: ]+\.ts)' "$SAFE_LOG" 2>/dev/null | sed -E 's/^[[:space:]]+//' | sort -u | paste -sd, -)"
[ -n "$TSC_ERROR_COUNT" ] || TSC_ERROR_COUNT="0"

CONFIG_SHA_AFTER="$(sha256sum "$CONFIG_FILE" 2>/dev/null | awk '{print $1}')"
PID_AFTER="$(systemctl --user show openclaw-gateway.service -p MainPID --value 2>/dev/null || true)"
QUEUE_AFTER="$(fingerprint_queue)"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$STATUS_AFTER" || fail_now "status_after_failed"
STATUS_AFTER_SHA="$(sha256sum "$STATUS_AFTER" | awk '{print $1}')"

if [ "$STATUS_BEFORE_SHA" = "$STATUS_AFTER_SHA" ]; then WORKTREE_PRESERVED="YES"; fi
if [ "$CONFIG_SHA_BEFORE" = "$CONFIG_SHA_AFTER" ]; then CONFIG_CHANGED="NO"; else CONFIG_CHANGED="YES"; fi
if [ "$PID_BEFORE" = "$PID_AFTER" ]; then SERVICE_PID_CHANGED="NO"; else SERVICE_PID_CHANGED="YES"; fi
if [ "$QUEUE_BEFORE" = "$QUEUE_AFTER" ]; then QUEUE_CHANGED="NO"; else QUEUE_CHANGED="YES"; fi

[ "$WORKTREE_PRESERVED" = "YES" ] || fail_now "worktree_changed_during_diagnostic"
[ "$CONFIG_CHANGED" = "NO" ] || fail_now "openclaw_config_changed_during_diagnostic"
[ "$SERVICE_PID_CHANGED" = "NO" ] || fail_now "openclaw_service_restarted_during_diagnostic"
[ "$QUEUE_CHANGED" = "NO" ] || fail_now "queue_changed_during_diagnostic"

if [ "$TSC_RC" = "0" ]; then
  RESULT="UNEXPECTEDLY_COMPILED"
  NEXT_ACTION="RERUN_FULL_PLUGIN_VALIDATION_V2"
else
  RESULT="DIAGNOSED"
  FAILURE_CODE="plugin_typescript_build_failed"
  NEXT_ACTION="READ_TYPESCRIPT_DIAGNOSTIC_EVIDENCE_AND_PATCH_PLUGIN_SOURCE"
fi

export TASK_ID STAMP RESULT FAILURE_CODE SOURCE_REF SOURCE_COMMIT OPENCLAW_VERSION NODE_VERSION NPM_VERSION NPM_INSTALL TSC_RC TSC_ERROR_COUNT TSC_ERROR_CODES TSC_ERROR_FILES WORKTREE_PRESERVED CONFIG_CHANGED SERVICE_PID_CHANGED QUEUE_CHANGED NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$SAFE_LOG" "$RESULT_JSON" <<'PY'
import json,os,sys
from pathlib import Path
safe_log=Path(sys.argv[1]).read_text(encoding='utf-8',errors='replace')
payload={
  'task_id':os.environ['TASK_ID'],
  'checked_at':os.environ['STAMP'],
  'result':os.environ['RESULT'],
  'failure_code':os.environ.get('FAILURE_CODE') or None,
  'source':{'ref':os.environ['SOURCE_REF'],'commit':os.environ['SOURCE_COMMIT']},
  'runtime':{'openclaw_version':os.environ['OPENCLAW_VERSION'],'node_version':os.environ['NODE_VERSION'],'npm_version':os.environ['NPM_VERSION']},
  'typescript':{'npm_install':os.environ['NPM_INSTALL'],'rc':os.environ['TSC_RC'],'error_count':int(os.environ['TSC_ERROR_COUNT'] or '0'),'error_codes':[x for x in os.environ.get('TSC_ERROR_CODES','').split(',') if x],'error_files':[x for x in os.environ.get('TSC_ERROR_FILES','').split(',') if x],'diagnostics':safe_log.splitlines()[:400]},
  'safety':{'worktree_preserved':os.environ['WORKTREE_PRESERVED']=='YES','openclaw_config_changed':os.environ['CONFIG_CHANGED']=='YES','service_pid_changed':os.environ['SERVICE_PID_CHANGED']=='YES','queue_changed':os.environ['QUEUE_CHANGED']=='YES','plugin_installed_or_enabled':False,'product_task_submitted':False,'secret_values_recorded':False},
  'next_action':os.environ['NEXT_ACTION'],
  'evidence':{'log_path':os.environ['EVIDENCE_LOG_REL'],'json_path':os.environ['EVIDENCE_JSON_REL'],'self_commit_sha_omitted_to_prevent_post_commit_log_drift':True}
}
Path(sys.argv[2]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
PY

{
  echo "checked_at=$(date -Is)"
  echo "task_id=$TASK_ID"
  echo "source_commit=$SOURCE_COMMIT"
  echo "openclaw_version=$OPENCLAW_VERSION"
  echo "node_version=$NODE_VERSION"
  echo "npm_version=$NPM_VERSION"
  echo "npm_install=$NPM_INSTALL"
  echo "tsc_rc=$TSC_RC"
  echo "tsc_error_count=$TSC_ERROR_COUNT"
  echo "tsc_error_codes=$TSC_ERROR_CODES"
  echo "tsc_error_files=$TSC_ERROR_FILES"
  echo "worktree_preserved=$WORKTREE_PRESERVED"
  echo "openclaw_config_changed=$CONFIG_CHANGED"
  echo "service_pid_changed=$SERVICE_PID_CHANGED"
  echo "queue_changed=$QUEUE_CHANGED"
  echo "secret_values_recorded=NO"
  echo "--- sanitized TypeScript diagnostics ---"
  cat "$SAFE_LOG"
} > "$TMP_ROOT/evidence.log"

python3 - "$TMP_ROOT/evidence.log" "$RESULT_JSON" <<'PY'
import re,sys
from pathlib import Path
patterns=[re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b')]
for f in sys.argv[1:]:
    text=Path(f).read_text(encoding='utf-8',errors='replace')
    if any(p.search(text) for p in patterns): raise SystemExit(1)
PY
if [ "$?" -eq 0 ]; then SECRET_SCAN="PASS"; else fail_now "diagnostic_secret_scan_failed"; fi

git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >/dev/null 2>&1 || fail_now "evidence_worktree_create_failed"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL" || fail_now "evidence_directory_create_failed"
cp "$TMP_ROOT/evidence.log" "$WORKTREE/$EVIDENCE_LOG_REL" || fail_now "evidence_log_copy_failed"
cp "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" || fail_now "evidence_json_copy_failed"
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native plugin TypeScript diagnostic $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main)" != "$(git -C "$WORKTREE" rev-parse origin/main)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ]; then EVIDENCE_REMOTE_VERIFIED="YES"; else fail_now "evidence_remote_sha_mismatch"; fi

summary
exit 0
