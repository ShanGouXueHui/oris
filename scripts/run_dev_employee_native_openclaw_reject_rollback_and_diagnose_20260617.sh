#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
SOURCE="$ORIS_REPO/scripts/dev_employee_native_openclaw_reject_rollback_and_diagnose_20260617.sh"
TMP_SCRIPT="$(mktemp /tmp/oris-native-openclaw-reject-diagnose-run-XXXXXX.sh)"

cleanup() {
  rm -f "$TMP_SCRIPT"
}
trap cleanup EXIT

summary_failed() {
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$1"
  echo "CURRENT_TASK_UPDATED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "PRODUCT_REPOSITORY_MUTATED=NO"
  echo "OPENCLAW_CONFIG_MUTATED=NO"
  echo "NEXT_ACTION=$2"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  summary_failed "wrong_linux_user" "RUN_AS_ADMIN"
  exit 1
fi

if [ ! -f "$SOURCE" ]; then
  summary_failed "diagnosis_source_missing" "PULL_ORIS_MAIN_AND_RETRY"
  exit 1
fi

python3 - "$SOURCE" "$TMP_SCRIPT" <<'PY'
import os
import sys
from pathlib import Path

source=Path(sys.argv[1])
target=Path(sys.argv[2])
text=source.read_text(encoding="utf-8")
start_marker='journalctl --user -u openclaw-gateway.service --since "2 hours ago" -n 500 --no-pager 2>/dev/null | python3 - "$JOURNAL_JSON" <<\'PY\'\n'
end_marker='RECENT_AUTH_MISMATCH_COUNT="$(python3 -c \'import json,sys; print(json.load(open(sys.argv[1]))["counts"]["auth_mismatch"])\' "$JOURNAL_JSON" 2>/dev/null || echo 0)"\n'
if start_marker not in text or end_marker not in text:
    print("expected journal block not found",file=sys.stderr)
    raise SystemExit(2)
start=text.index(start_marker)
end=text.index(end_marker,start)
replacement='''JOURNAL_RAW="$TMP_ROOT/openclaw-gateway-journal.raw"
journalctl --user -u openclaw-gateway.service --since "2 hours ago" -n 500 --no-pager > "$JOURNAL_RAW" 2>/dev/null || true
python3 - "$JOURNAL_RAW" "$JOURNAL_JSON" <<'PY'
import json,re,sys
from pathlib import Path
source=Path(sys.argv[1])
out=Path(sys.argv[2])
lines=[]
counts={"auth_mismatch":0,"unauthorized":0,"forbidden":0,"origin":0,"websocket":0}
patterns={
 "auth_mismatch":re.compile(r"auth(?:entication)?[^\\n]{0,80}mismatch|credential[^\\n]{0,80}(?:reject|mismatch)",re.I),
 "unauthorized":re.compile(r"unauthori[sz]ed|\\b401\\b",re.I),
 "forbidden":re.compile(r"forbidden|\\b403\\b",re.I),
 "origin":re.compile(r"origin",re.I),
 "websocket":re.compile(r"websocket|\\bws\\b|upgrade",re.I),
}
secret=re.compile(r"(?i)(token|password|secret|authorization)(\\s*[=:]\\s*|\\s+)([^\\s,;]+)")
long_id=re.compile(r"\\b[a-f0-9]{24,}\\b",re.I)
url_query=re.compile(r"(https?://[^\\s?]+)\\?[^\\s]+")
raw_text=source.read_text(encoding="utf-8",errors="replace") if source.exists() else ""
for raw in raw_text.splitlines():
    matched=[]
    for name,p in patterns.items():
        if p.search(raw):
            counts[name]+=1
            matched.append(name)
    if not matched:
        continue
    line=secret.sub(r"\\1\\2<redacted>",raw.strip())
    line=long_id.sub("<redacted-id>",line)
    line=url_query.sub(r"\\1?<redacted-query>",line)
    lines.append({"classes":matched,"message":line[:500]})
out.write_text(json.dumps({"counts":counts,"events":lines[-100:]},ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
PY
'''
patched=text[:start]+replacement+text[end:]
target.write_text(patched,encoding="utf-8")
os.chmod(target,0o700)
PY
if [ "$?" -ne 0 ]; then
  summary_failed "temporary_journal_patch_failed" "INSPECT_DIAGNOSIS_SCRIPT_VERSION"
  exit 1
fi

if ! bash -n "$TMP_SCRIPT" >/dev/null 2>&1; then
  summary_failed "patched_diagnosis_script_syntax_invalid" "REPAIR_DIAGNOSIS_SCRIPT"
  exit 1
fi

bash "$TMP_SCRIPT"
exit "$?"
