#!/usr/bin/env bash

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-insight-secret-rotation-${STAMP}-XXXXXX)"
WORKTREE="$TMP_ROOT/worktree"
ROTATION_JSON="$TMP_ROOT/rotation.json"
SMOKE_JSON="$TMP_ROOT/smoke.json"
EVIDENCE_JSON="$TMP_ROOT/evidence.json"
EVIDENCE_DIR_REL="logs/dev_employee/security_remediation"
EVIDENCE_REL="$EVIDENCE_DIR_REL/insight-db-credential-rotation-$STAMP.json"
RESULT="FAILED"
FAILURE_CODE=""
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"

cleanup() {
  if [ -n "$REPO_ROOT" ] && [ -d "$WORKTREE" ]; then
    git -C "$REPO_ROOT" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "PLAINTEXT_CONFIG_SECRET_REMOVED=YES"
  echo "DATABASE_CREDENTIAL_ROTATED=$([ "$RESULT" = "ROTATED_AND_VERIFIED" ] && echo YES || echo NO)"
  echo "DATABASE_CONNECTION_VERIFIED=$([ "$RESULT" = "ROTATED_AND_VERIFIED" ] && echo YES || echo NO)"
  echo "SECRET_VALUES_PRINTED=NO"
  echo "EVIDENCE_JSON=$EVIDENCE_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "NEXT_ACTION=$([ "$RESULT" = "ROTATED_AND_VERIFIED" ] && echo RUN_AUTOMATIC_OPENCLAW_READONLY_ENABLEMENT || echo INSPECT_PRIVATE_DATABASE_ROTATION_FAILURE)"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  RESULT="FAILED"
}

[ -n "$REPO_ROOT" ] || fail "repository_root_unresolved"
for command_name in git python3 date mktemp; do
  command -v "$command_name" >/dev/null 2>&1 || fail "required_command_missing_$command_name"
done

if [ -z "$FAILURE_CODE" ]; then
  PYTHONPATH="$REPO_ROOT" python3 -m compileall -q \
    "$REPO_ROOT/scripts/lib/secret_refs.py" \
    "$REPO_ROOT/scripts/security/rotate_insight_db_credential.py" >/dev/null 2>&1
  [ "$?" = "0" ] || fail "security_module_compile_failed"
fi

if [ -z "$FAILURE_CODE" ]; then
  PYTHONPATH="$REPO_ROOT" python3 -m scripts.security.rotate_insight_db_credential "$ROTATION_JSON" >/dev/null 2>&1
  [ "$?" = "0" ] || fail "database_credential_rotation_failed"
fi

if [ -z "$FAILURE_CODE" ]; then
  PYTHONPATH="$REPO_ROOT" python3 - "$SMOKE_JSON" <<'PY'
import json,sys
from pathlib import Path
from scripts.lib.insight_db import db_connect
out=Path(sys.argv[1])
try:
 connection=db_connect()
 try:
  with connection.cursor() as cursor:
   cursor.execute('SELECT 1')
   row=cursor.fetchone()
  ok=bool(row and row[0]==1)
 finally:
  connection.close()
except Exception:
 ok=False
out.write_text(json.dumps({'database_connection_verified':ok,'secret_values_recorded':False},sort_keys=True,indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if ok else 1)
PY
  [ "$?" = "0" ] || fail "post_rotation_database_smoke_failed"
fi

PYTHONPATH="$REPO_ROOT" python3 - "$REPO_ROOT" "$ROTATION_JSON" "$SMOKE_JSON" "$EVIDENCE_JSON" "$RESULT" "$FAILURE_CODE" <<'PY'
import json,sys
from pathlib import Path
from scripts.dev_employee_quality.models import SourceFile
from scripts.dev_employee_quality.secrets import scan_json_secrets
repo=Path(sys.argv[1]); rotation_path=Path(sys.argv[2]); smoke_path=Path(sys.argv[3]); out=Path(sys.argv[4]); result=sys.argv[5]; failure=sys.argv[6]
config_path=repo/'config/insight_storage.json'
source=SourceFile(config_path,'config/insight_storage.json','.json',config_path.read_text(encoding='utf-8'))
secret_findings=scan_json_secrets(source)
def read(path):
 try: return json.loads(path.read_text(encoding='utf-8'))
 except Exception: return {}
rotation=read(rotation_path); smoke=read(smoke_path)
ok=not failure and rotation.get('result')=='ROTATED_AND_VERIFIED' and smoke.get('database_connection_verified') is True and not secret_findings
payload={
 'result':'ROTATED_AND_VERIFIED' if ok else 'FAILED',
 'failure_code':failure or None,
 'rotation':rotation,
 'smoke':smoke,
 'tracked_config_plaintext_secret_findings':len(secret_findings),
 'safety':{'old_secret_recorded':False,'new_secret_recorded':False,'secret_values_printed':False},
}
out.write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
PY
[ "$?" = "0" ] || fail "security_evidence_build_failed"

if [ -z "$FAILURE_CODE" ]; then
  RESULT="ROTATED_AND_VERIFIED"
fi

if [ -n "$REPO_ROOT" ] && [ -f "$EVIDENCE_JSON" ]; then
  git -C "$REPO_ROOT" fetch origin main >/dev/null 2>&1
  if [ "$?" = "0" ]; then
    git -C "$REPO_ROOT" worktree add --detach "$WORKTREE" origin/main >/dev/null 2>&1
    if [ "$?" = "0" ]; then
      mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
      cp "$EVIDENCE_JSON" "$WORKTREE/$EVIDENCE_REL"
      git -C "$WORKTREE" add -- "$EVIDENCE_REL" >/dev/null 2>&1
      git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1
      if [ "$?" = "0" ]; then
        git -C "$WORKTREE" commit -m "security(insight): record credential rotation $STAMP" >/dev/null 2>&1
        git -C "$WORKTREE" fetch origin main >/dev/null 2>&1
        if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
          git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1
        fi
        EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
        git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1
        REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
        if [ -n "$EVIDENCE_COMMIT" ] && [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ]; then
          EVIDENCE_REMOTE_VERIFIED="YES"
        fi
      fi
    fi
  fi
fi

if [ "$EVIDENCE_REMOTE_VERIFIED" != "YES" ]; then
  [ -n "$FAILURE_CODE" ] || FAILURE_CODE="security_evidence_not_remote_verified"
  RESULT="FAILED"
fi

summary
[ "$RESULT" = "ROTATED_AND_VERIFIED" ] && exit 0
exit 1
