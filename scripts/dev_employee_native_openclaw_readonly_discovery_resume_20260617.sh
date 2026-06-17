#!/usr/bin/env bash

# Narrow corrective runner for the 2026-06-17 native OpenClaw read-only discovery.
# It patches only the temporary execution copy so generated evidence has canonical
# LF line endings, no trailing whitespace, and useful read-only dirty-path detail.

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
SOURCE="$ORIS_REPO/scripts/dev_employee_native_openclaw_readonly_discovery_20260617.sh"
TMP_SCRIPT="$(mktemp /tmp/oris-native-openclaw-discovery-resume-XXXXXX.sh)"

cleanup() {
  rm -f "$TMP_SCRIPT"
}
trap cleanup EXIT

failure_summary() {
  local code="$1"
  local action="$2"
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "DISCOVERY_COMPLETE=NO"
  echo "FAILURE_CODE=$code"
  echo "CONFIG_OR_SERVICE_CHANGED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=$action"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  failure_summary "wrong_linux_user" "RUN_AS_ADMIN"
  exit 1
fi

if [ ! -f "$SOURCE" ]; then
  failure_summary "discovery_source_missing" "PULL_ORIS_MAIN_AND_RETRY"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  failure_summary "python3_missing" "RESTORE_REQUIRED_HOST_TOOL"
  exit 1
fi

python3 - "$SOURCE" "$TMP_SCRIPT" <<'PY'
import os
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")

evidence_old = '''mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
cp "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL"
cp "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL"
if ! git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL"; then fail_now "evidence_git_add_failed" "INSPECT_DETACHED_WORKTREE"; fi
if ! git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1; then fail_now "evidence_diff_check_failed" "REPAIR_EVIDENCE_FORMAT"; fi
'''

evidence_new = '''mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_NORMALIZE_EVIDENCE'
import json
import sys
from pathlib import Path

source_log = Path(sys.argv[1])
target_log = Path(sys.argv[2])
source_json = Path(sys.argv[3])
target_json = Path(sys.argv[4])

log_text = source_log.read_text(encoding="utf-8", errors="replace")
normalized_lines = [line.rstrip(" \\t\\r") for line in log_text.splitlines()]
target_log.write_text("\\n".join(normalized_lines) + "\\n", encoding="utf-8")

payload = json.loads(source_json.read_text(encoding="utf-8"))
target_json.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\\n",
    encoding="utf-8",
)
PY_NORMALIZE_EVIDENCE
if [ "$?" -ne 0 ]; then fail_now "evidence_normalization_failed" "INSPECT_GENERATED_EVIDENCE"; fi
if ! git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL"; then fail_now "evidence_git_add_failed" "INSPECT_DETACHED_WORKTREE"; fi
if ! git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1; then
  git -C "$WORKTREE" diff --cached --check >> "$RUN_LOG" 2>&1 || true
  fail_now "evidence_diff_check_failed_after_normalization" "INSPECT_GENERATED_EVIDENCE"
fi
'''

baseline_old = '''    _,status,_=run(repo,"status","--porcelain","--untracked-files=all"); rc,ls,_=run(repo,"ls-remote","--heads","origin","refs/heads/main"); remote_main=ls.split()[0] if rc==0 and ls else ""
    return {"label":label,"exists":True,"path":str(repo),"head":head,"branch":branch,"remote":remote,"remote_main":remote_main,"clean":not bool(status),"status_entry_count":len(status.splitlines()) if status else 0}
'''

baseline_new = '''    _,status,_=run(repo,"status","--porcelain","--untracked-files=all"); rc,ls,_=run(repo,"ls-remote","--heads","origin","refs/heads/main"); remote_main=ls.split()[0] if rc==0 and ls else ""
    status_entries=[]
    for line in status.splitlines():
        code=line[:2]
        path=line[3:] if len(line)>3 else ""
        status_entries.append({"code":code,"path":path})
    return {"label":label,"exists":True,"path":str(repo),"head":head,"branch":branch,"remote":remote,"remote_main":remote_main,"clean":not bool(status),"status_entry_count":len(status_entries),"status_entries":status_entries}
'''

if evidence_old not in text:
    print("expected evidence block not found", file=sys.stderr)
    raise SystemExit(2)
patched = text.replace(evidence_old, evidence_new, 1)

if baseline_old not in patched:
    print("expected repository baseline block not found", file=sys.stderr)
    raise SystemExit(3)
patched = patched.replace(baseline_old, baseline_new, 1)

target.write_text(patched, encoding="utf-8")
os.chmod(target, 0o700)
PY
PATCH_RC="$?"

if [ "$PATCH_RC" -ne 0 ]; then
  failure_summary "temporary_patch_failed" "INSPECT_DISCOVERY_SCRIPT_VERSION"
  exit 1
fi

if ! bash -n "$TMP_SCRIPT" >/dev/null 2>&1; then
  failure_summary "patched_script_syntax_invalid" "REPAIR_DISCOVERY_RESUME_SCRIPT"
  exit 1
fi

bash "$TMP_SCRIPT"
exit "$?"
