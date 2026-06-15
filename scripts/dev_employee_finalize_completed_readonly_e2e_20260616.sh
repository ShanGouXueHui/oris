#!/usr/bin/env bash

TASK_ID="${1:-goal-oris-final-acceptance-api-readonly-e2e-20260616-044030}"
ORIS="/home/admin/projects/oris"
PRODUCT="/home/admin/projects/oris-final-acceptance-api"
ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
PATCHER="$ORIS/scripts/dev_employee_fix_terminal_queue_paths_20260616.py"
LOG_DIR="$ORIS/logs/dev_employee/web_console_public_submit_e2e"
STAMP="$(date +%Y%m%d%H%M%S)"
MAIN_LOG="$LOG_DIR/${TASK_ID}.finalize-$STAMP.log"
STATUS_JSON="$LOG_DIR/${TASK_ID}.final-status-$STAMP.json"
VERIFY_JSON="$LOG_DIR/${TASK_ID}.final-verification-$STAMP.json"
PYCOMPILE_LOG="$LOG_DIR/${TASK_ID}.final-pycompile-$STAMP.txt"
PYTEST_LOG="$LOG_DIR/${TASK_ID}.final-pytest-$STAMP.txt"
ENDPOINT_LOG="$LOG_DIR/${TASK_ID}.final-endpoint-$STAMP.txt"

RESULT="FAILED"
FINAL_STATUS="unknown"
CANONICAL_STATUS="unknown"
TERMINAL="false"
FAILURE_CODE=""
PRODUCT_PY_COMPILE="NOT_RUN"
PRODUCT_PYTEST="NOT_RUN"
ENDPOINT_CONTRACT="NOT_RUN"
HOST_PYTEST_EVIDENCE="NOT_VERIFIED"
STRICT_RESULT_SCHEMA="NOT_VERIFIED"
PRODUCT_COMMIT_SHA=""
PRODUCT_REMOTE_SHA=""
PRODUCT_LOCAL_HEAD=""
PRODUCT_REMOTE_MAIN=""
PRODUCT_SHA_MATCH="NO"
PRODUCT_WORKTREE_CLEAN="NO"
ORIS_EVIDENCE_COMMIT_SHA=""
ORIS_EVIDENCE_REMOTE_SHA=""
ORIS_EVIDENCE_INDEX_COMMIT_SHA=""
ORIS_EVIDENCE_ON_REMOTE="NO"
ORIS_INDEX_ON_REMOTE="NO"
LOG_COMMIT=""
NEXT_ACTION="INSPECT_GITHUB_EVIDENCE"
STASHED="NO"

mkdir -p "$LOG_DIR"
: > "$MAIN_LOG"

log() {
  printf '%s\n' "$*" | tee -a "$MAIN_LOG"
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FINAL_STATUS=$FINAL_STATUS"
  echo "CANONICAL_STATUS=$CANONICAL_STATUS"
  echo "TERMINAL=$TERMINAL"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "PRODUCT_PY_COMPILE=$PRODUCT_PY_COMPILE"
  echo "PRODUCT_PYTEST=$PRODUCT_PYTEST"
  echo "ENDPOINT_CONTRACT=$ENDPOINT_CONTRACT"
  echo "HOST_PYTEST_EVIDENCE=$HOST_PYTEST_EVIDENCE"
  echo "STRICT_RESULT_SCHEMA=$STRICT_RESULT_SCHEMA"
  echo "PRODUCT_COMMIT_SHA=$PRODUCT_COMMIT_SHA"
  echo "PRODUCT_REMOTE_SHA=$PRODUCT_REMOTE_SHA"
  echo "PRODUCT_LOCAL_HEAD=$PRODUCT_LOCAL_HEAD"
  echo "PRODUCT_REMOTE_MAIN=$PRODUCT_REMOTE_MAIN"
  echo "PRODUCT_SHA_MATCH=$PRODUCT_SHA_MATCH"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "ORIS_EVIDENCE_COMMIT_SHA=$ORIS_EVIDENCE_COMMIT_SHA"
  echo "ORIS_EVIDENCE_REMOTE_SHA=$ORIS_EVIDENCE_REMOTE_SHA"
  echo "ORIS_EVIDENCE_INDEX_COMMIT_SHA=$ORIS_EVIDENCE_INDEX_COMMIT_SHA"
  echo "ORIS_EVIDENCE_ON_REMOTE=$ORIS_EVIDENCE_ON_REMOTE"
  echo "ORIS_INDEX_ON_REMOTE=$ORIS_INDEX_ON_REMOTE"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "WEB_CONSOLE_SERVICE=$(systemctl --user is-active oris-dev-employee-web-console.service 2>/dev/null || true)"
  echo "INTAKE_SERVICE=$(systemctl --user is-active oris-dev-employee-intake.service 2>/dev/null || true)"
  echo "BRIDGE_SERVICE=$(systemctl --user is-active oris-dev-employee-bridge.service 2>/dev/null || true)"
  echo "REAL_PRODUCT_TASK_SUBMITTED=YES"
  echo "NEW_PRODUCT_TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  log "FAILURE_CODE=$FAILURE_CODE"
  if [ "$STASHED" = "YES" ]; then
    git stash pop >> "$MAIN_LOG" 2>&1 || true
  fi
  summary
  exit 1
}

if [ "$(id -un)" != "admin" ]; then
  fail "wrong_linux_user" "RUN_AS_ADMIN"
fi

cd "$ORIS" || fail "oris_directory_missing" "RESTORE_ORIS_REPOSITORY"

if ! git diff --quiet -- scripts/dev_employee_diagnose_codex_failed_task.sh; then
  git stash push -m "temp-diagnose-before-terminal-path-fix" -- scripts/dev_employee_diagnose_codex_failed_task.sh >> "$MAIN_LOG" 2>&1 || fail "diagnose_script_stash_failed" "INSPECT_GIT_STATE"
  STASHED="YES"
fi

git fetch origin main >> "$MAIN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git rebase origin/main >> "$MAIN_LOG" 2>&1 || fail "oris_rebase_failed" "INSPECT_ORIS_REBASE"

python3 "$PATCHER" --task-id "$TASK_ID" >> "$MAIN_LOG" 2>&1 || fail "terminal_queue_path_patch_failed" "INSPECT_QUEUE_PATH_PATCH"
python3 -m py_compile \
  scripts/dev_employee_fix_terminal_queue_paths_20260616.py \
  scripts/dev_employee_supervised_bridge_v2.py \
  scripts/dev_employee_intake_api.py >> "$MAIN_LOG" 2>&1 || fail "platform_compile_failed" "FIX_PLATFORM_STATIC_CHECKS"

git diff --check -- scripts/dev_employee_supervised_bridge_v2.py scripts/dev_employee_intake_api.py >> "$MAIN_LOG" 2>&1 || fail "platform_diff_check_failed" "FIX_PLATFORM_DIFF"
git add -- scripts/dev_employee_supervised_bridge_v2.py scripts/dev_employee_intake_api.py >> "$MAIN_LOG" 2>&1 || fail "platform_git_add_failed" "INSPECT_GIT_STATE"
if ! git diff --cached --quiet -- scripts/dev_employee_supervised_bridge_v2.py scripts/dev_employee_intake_api.py; then
  git commit --only -m "fix(dev-employee): canonicalize terminal queue paths" -- scripts/dev_employee_supervised_bridge_v2.py scripts/dev_employee_intake_api.py >> "$MAIN_LOG" 2>&1 || fail "platform_commit_failed" "INSPECT_PLATFORM_COMMIT"
  git push origin main >> "$MAIN_LOG" 2>&1 || fail "platform_push_failed" "RESOLVE_ORIS_GIT_PUSH"
fi

systemctl --user restart oris-dev-employee-intake.service >> "$MAIN_LOG" 2>&1 || fail "intake_restart_failed" "INSPECT_INTAKE_SERVICE"
systemctl --user restart oris-dev-employee-bridge.service >> "$MAIN_LOG" 2>&1 || fail "bridge_restart_failed" "INSPECT_BRIDGE_SERVICE"
sleep 2

TOKEN="$(awk -F= '/^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=/ {print substr($0, index($0, "=")+1)}' "$ENV_FILE" | tail -n 1)"
[ -n "$TOKEN" ] || fail "console_token_missing" "RESTORE_CONSOLE_TOKEN"
HTTP_CODE="$(curl -sS -o "$STATUS_JSON" -w '%{http_code}' -H "X-ORIS-Console-Token: $TOKEN" "http://127.0.0.1:18893/api/goals/$TASK_ID" || true)"
TOKEN=""
[ "$HTTP_CODE" = "200" ] || fail "status_api_http_$HTTP_CODE" "INSPECT_STATUS_API"

readarray -t VALUES < <(python3 - "$STATUS_JSON" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding='utf-8'))
ev=p.get('github_evidence') or {}
queue=p.get('queue') or []
done={}
for item in queue:
    if item.get('suffix') == 'done' and isinstance(item.get('data'), dict):
        candidate=item['data']
        idx=candidate.get('oris_evidence_index_result') or {}
        if candidate.get('status') == 'completed' and idx.get('commit_sha'):
            done=candidate
            break
idx=done.get('oris_evidence_index_result') or {}
labels={str(x.get('label')) for x in (ev.get('files') or []) if isinstance(x, dict)}
values=[
    p.get('status') or 'unknown',
    p.get('canonical_status') or p.get('status') or 'unknown',
    'true' if p.get('terminal') is True else 'false',
    p.get('failure_code') or '',
    ev.get('product_commit_sha') or '',
    ev.get('product_remote_sha') or '',
    ev.get('oris_evidence_commit_sha') or '',
    ev.get('oris_evidence_remote_sha') or '',
    idx.get('commit_sha') or '',
    'PASS' if ev.get('strict_result_schema') is True else 'FAILED',
    'PASS' if 'host_pytest_log' in labels else 'FAILED',
]
for v in values:
    print(v)
PY
)
FINAL_STATUS="${VALUES[0]}"
CANONICAL_STATUS="${VALUES[1]}"
TERMINAL="${VALUES[2]}"
FAILURE_CODE="${VALUES[3]}"
PRODUCT_COMMIT_SHA="${VALUES[4]}"
PRODUCT_REMOTE_SHA="${VALUES[5]}"
ORIS_EVIDENCE_COMMIT_SHA="${VALUES[6]}"
ORIS_EVIDENCE_REMOTE_SHA="${VALUES[7]}"
ORIS_EVIDENCE_INDEX_COMMIT_SHA="${VALUES[8]}"
STRICT_RESULT_SCHEMA="${VALUES[9]}"
HOST_PYTEST_EVIDENCE="${VALUES[10]}"

[ "$FINAL_STATUS" = "completed" ] || fail "task_not_completed:$FINAL_STATUS" "INSPECT_TASK_STATUS"
[ "$CANONICAL_STATUS" = "completed" ] || fail "canonical_status_not_completed:$CANONICAL_STATUS" "INSPECT_TASK_STATUS"
[ "$TERMINAL" = "true" ] || fail "task_not_terminal" "INSPECT_TASK_STATUS"
[ -n "$ORIS_EVIDENCE_INDEX_COMMIT_SHA" ] || fail "evidence_index_commit_missing" "INSPECT_DONE_RECORD"

PYTHON_BIN="$PRODUCT/.venv/bin/python"
[ -x "$PYTHON_BIN" ] || fail "product_python_missing" "RESTORE_PRODUCT_VENV"
"$PYTHON_BIN" -m py_compile app/main.py > "$PYCOMPILE_LOG" 2>&1
[ "$?" -eq 0 ] || fail "product_py_compile_failed" "INSPECT_PRODUCT_COMPILE_LOG"
PRODUCT_PY_COMPILE="PASS"
"$PYTHON_BIN" -m pytest -q > "$PYTEST_LOG" 2>&1
[ "$?" -eq 0 ] || fail "product_pytest_failed" "INSPECT_PRODUCT_PYTEST_LOG"
PRODUCT_PYTEST="PASS"

"$PYTHON_BIN" - <<'PY' > "$ENDPOINT_LOG" 2>&1
import json
from fastapi.testclient import TestClient
from app.main import app
r=TestClient(app).get('/readonly-e2e')
body=r.json()
print(json.dumps({'status_code': r.status_code, 'body': body}, sort_keys=True))
raise SystemExit(0 if r.status_code == 200 and body == {'readonly_e2e': True} else 1)
PY
[ "$?" -eq 0 ] || fail "endpoint_contract_failed" "INSPECT_ENDPOINT_LOG"
ENDPOINT_CONTRACT="PASS"

PRODUCT_LOCAL_HEAD="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_MAIN="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
TRACKED_DIRTY="$(git -C "$PRODUCT" status --porcelain --untracked-files=no)"
[ -z "$TRACKED_DIRTY" ] && PRODUCT_WORKTREE_CLEAN="YES"
if [ -n "$PRODUCT_COMMIT_SHA" ] && [ "$PRODUCT_COMMIT_SHA" = "$PRODUCT_REMOTE_SHA" ] && [ "$PRODUCT_COMMIT_SHA" = "$PRODUCT_LOCAL_HEAD" ] && [ "$PRODUCT_COMMIT_SHA" = "$PRODUCT_REMOTE_MAIN" ]; then
  PRODUCT_SHA_MATCH="YES"
fi
[ "$PRODUCT_SHA_MATCH" = "YES" ] || fail "product_sha_mismatch" "INSPECT_PRODUCT_GIT_STATE"
[ "$PRODUCT_WORKTREE_CLEAN" = "YES" ] || fail "product_worktree_dirty" "INSPECT_PRODUCT_GIT_STATE"
[ "$HOST_PYTEST_EVIDENCE" = "PASS" ] || fail "host_pytest_evidence_missing" "INSPECT_ORIS_EVIDENCE"
[ "$STRICT_RESULT_SCHEMA" = "PASS" ] || fail "strict_result_schema_missing" "INSPECT_ORIS_EVIDENCE"
[ "$ORIS_EVIDENCE_COMMIT_SHA" = "$ORIS_EVIDENCE_REMOTE_SHA" ] || fail "oris_evidence_sha_mismatch" "INSPECT_ORIS_EVIDENCE"

git fetch origin main >> "$MAIN_LOG" 2>&1 || fail "final_oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git merge-base --is-ancestor "$ORIS_EVIDENCE_COMMIT_SHA" origin/main && ORIS_EVIDENCE_ON_REMOTE="YES"
git merge-base --is-ancestor "$ORIS_EVIDENCE_INDEX_COMMIT_SHA" origin/main && ORIS_INDEX_ON_REMOTE="YES"
[ "$ORIS_EVIDENCE_ON_REMOTE" = "YES" ] || fail "oris_evidence_not_on_remote" "INSPECT_ORIS_REMOTE"
[ "$ORIS_INDEX_ON_REMOTE" = "YES" ] || fail "oris_index_not_on_remote" "INSPECT_ORIS_REMOTE"

python3 - "$VERIFY_JSON" <<PY
import json
payload = {
  "task_id": "$TASK_ID",
  "result": "PASS",
  "product_commit_sha": "$PRODUCT_COMMIT_SHA",
  "product_remote_sha": "$PRODUCT_REMOTE_SHA",
  "oris_evidence_commit_sha": "$ORIS_EVIDENCE_COMMIT_SHA",
  "oris_evidence_index_commit_sha": "$ORIS_EVIDENCE_INDEX_COMMIT_SHA",
  "product_py_compile": "PASS",
  "product_pytest": "PASS",
  "endpoint_contract": "PASS",
  "host_pytest_evidence": "PASS",
  "strict_result_schema": "PASS"
}
open("$VERIFY_JSON", "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
PY

RESULT="PASS"
NEXT_ACTION="FINAL_ACCEPTANCE_COMPLETE"
log "FINAL_ACCEPTANCE=PASS"

REL_MAIN="${MAIN_LOG#$ORIS/}"
REL_STATUS="${STATUS_JSON#$ORIS/}"
REL_VERIFY="${VERIFY_JSON#$ORIS/}"
REL_COMPILE="${PYCOMPILE_LOG#$ORIS/}"
REL_PYTEST="${PYTEST_LOG#$ORIS/}"
REL_ENDPOINT="${ENDPOINT_LOG#$ORIS/}"
git add -- "$REL_MAIN" "$REL_STATUS" "$REL_VERIFY" "$REL_COMPILE" "$REL_PYTEST" "$REL_ENDPOINT" >> "$MAIN_LOG" 2>&1 || fail "final_log_add_failed" "INSPECT_ORIS_GIT_STATE"
git commit --only -m "test(dev-employee): finalize completed readonly E2E $TASK_ID" -- "$REL_MAIN" "$REL_STATUS" "$REL_VERIFY" "$REL_COMPILE" "$REL_PYTEST" "$REL_ENDPOINT" >> "$MAIN_LOG" 2>&1 || fail "final_log_commit_failed" "INSPECT_FINAL_LOG_COMMIT"
git push origin main >> "$MAIN_LOG" 2>&1 || fail "final_log_push_failed" "RESOLVE_ORIS_GIT_PUSH"
LOG_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"

if [ "$STASHED" = "YES" ]; then
  git stash pop >> "$MAIN_LOG" 2>&1 || true
  STASHED="NO"
fi

summary
exit 0
