#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
PRODUCT_TASK_ID="chat-oris-final-acceptance-api-20260617-051313-c802347ff17c"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
PRODUCT_REMOTE_REPO="ShanGouXueHui/oris-final-acceptance-api"
PRODUCT_BASE_COMMIT="927f1968cc86bfd5213670f4eaa171fc1a3be620"
SUPPLEMENTAL_ACCEPTANCE_COMMIT="b479436a51bb1731e79fcfe98b2ec3d8b4683abd"
SUPPLEMENTAL_ACCEPTANCE_JSON="logs/dev_employee/native_openclaw_ui_acceptance/native-openclaw-ui-supplemental-acceptance-20260617T213905Z.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ISO_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-native-ui-product-completion-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/completion.log"
RESULT_JSON="$TMP_ROOT/completion.json"
README_PATCH="$TMP_ROOT/readme.patch"
PYTEST_LOG="$TMP_ROOT/pytest.log"
WORKTREE="$TMP_ROOT/oris-evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/commercial_native_openclaw_completion"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/native-openclaw-product-completion-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/native-openclaw-product-completion-$STAMP.json"
COMPLETION_DOC_REL="memory/dev_employee/COMMERCIAL_NATIVE_OPENCLAW_UI_COMPLETION_2026-06-17.md"
CURRENT_STATE_REL="memory/dev_employee/CURRENT_STATE_2026-06-17_NATIVE_UI_COMPLETED.md"
HANDOFF_REL="memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-17_NATIVE_UI_COMPLETED.md"
CURRENT_TASK_JSON_REL="memory/dev_employee/current_task.json"
CURRENT_TASK_MD_REL="memory/dev_employee/current_task.md"
CONTEXT_INDEX_REL="memory/dev_employee/CONTEXT_INDEX.md"

RESULT="FAILED"
FAILURE_CODE=""
ACTIVE_QUEUE_COUNT="unknown"
README_PATCH_VALID="NO"
README_CAPABILITIES_DOCUMENTED="NO"
PY_COMPILE="NOT_RUN"
PYTEST="NOT_RUN"
ROUTE_CONTRACT="NOT_RUN"
PRODUCT_COMMIT=""
PRODUCT_REMOTE_MAIN=""
PRODUCT_SHA_VERIFIED="NO"
PRODUCT_WORKTREE_CLEAN="NO"
PRODUCT_CHANGED_FILES=""
ORIS_CONTEXT_UPDATED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_PRODUCT_README_COMPLETION_FAILURE"

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
  echo "PRODUCT_TASK_ID=$PRODUCT_TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "ACTIVE_QUEUE_COUNT=$ACTIVE_QUEUE_COUNT"
  echo "README_PATCH_VALID=$README_PATCH_VALID"
  echo "README_CAPABILITIES_DOCUMENTED=$README_CAPABILITIES_DOCUMENTED"
  echo "PY_COMPILE=$PY_COMPILE"
  echo "PYTEST=$PYTEST"
  echo "ROUTE_CONTRACT=$ROUTE_CONTRACT"
  echo "PRODUCT_BASE_COMMIT=$PRODUCT_BASE_COMMIT"
  echo "PRODUCT_COMMIT=$PRODUCT_COMMIT"
  echo "PRODUCT_REMOTE_MAIN=$PRODUCT_REMOTE_MAIN"
  echo "PRODUCT_SHA_VERIFIED=$PRODUCT_SHA_VERIFIED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "PRODUCT_CHANGED_FILES=$PRODUCT_CHANGED_FILES"
  echo "ORIS_CONTEXT_UPDATED=$ORIS_CONTEXT_UPDATED"
  echo "SECRET_SCAN=$SECRET_SCAN"
  echo "EVIDENCE_LOG=$EVIDENCE_LOG_REL"
  echo "EVIDENCE_JSON=$EVIDENCE_JSON_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "OPENCLAW_CONFIG_MUTATED=NO"
  echo "NGINX_CHANGED=NO"
  echo "PRODUCT_FEATURE_CODE_MUTATED=NO"
  echo "NEW_PRODUCT_TASK_SUBMITTED=NO"
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

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user" "RUN_AS_ADMIN"; fi
for cmd in git python3 sha256sum find awk grep sed; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$PRODUCT_REPO/README.md" ] || fail_now "product_readme_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$PRODUCT_REPO/app/main.py" ] || fail_now "product_main_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$PRODUCT_REPO/tests/test_tasks_api.py" ] || fail_now "product_tests_missing" "RESTORE_PRODUCT_REPOSITORY"

log "CHECKED_AT=$ISO_TIME"
log "TASK_ID=$TASK_ID"
log "PRODUCT_TASK_ID=$PRODUCT_TASK_ID"
log "MODE=COMPLETE_EXISTING_README_GAP_AFTER_NATIVE_OPENCLAW_ACCEPTANCE"
log "SUPPLEMENTAL_ACCEPTANCE_COMMIT=$SUPPLEMENTAL_ACCEPTANCE_COMMIT"
log "NEW_PRODUCT_TASK_SUBMITTED=NO"
log "PRODUCT_FEATURE_CODE_MUTATED=NO"
log "OPENCLAW_CONFIG_MUTATED=NO"
log "NGINX_CHANGED=NO"

ACTIVE_QUEUE_COUNT="$(find "$ORIS_REPO/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' -o -name '*.claimed.json' -o -name '*.planning.json' -o -name '*.executing.json' -o -name '*.committing.json' -o -name '*.pushing.json' -o -name '*.cancelling.json' \) 2>/dev/null | wc -l | tr -d ' ')"
log "ACTIVE_QUEUE_COUNT=$ACTIVE_QUEUE_COUNT"
[ "$ACTIVE_QUEUE_COUNT" = "0" ] || fail_now "active_queue_present" "WAIT_FOR_QUEUE_TO_DRAIN"

PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_STAGED_BEFORE="$(git -C "$PRODUCT_REPO" diff --cached --name-only 2>/dev/null || true)"
MAIN_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/app/main.py" | awk '{print $1}')"
TEST_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/tests/test_tasks_api.py" | awk '{print $1}')"
README_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/README.md" | awk '{print $1}')"

log "PRODUCT_HEAD_BEFORE=$PRODUCT_HEAD_BEFORE"
log "PRODUCT_REMOTE_BEFORE=$PRODUCT_REMOTE_BEFORE"
log "PRODUCT_STATUS_BEFORE=$PRODUCT_STATUS_BEFORE"
log "PRODUCT_STAGED_BEFORE=${PRODUCT_STAGED_BEFORE:-<empty>}"
log "MAIN_SHA256_BEFORE=$MAIN_HASH_BEFORE"
log "TEST_SHA256_BEFORE=$TEST_HASH_BEFORE"
log "README_SHA256_BEFORE=$README_HASH_BEFORE"

[ "$PRODUCT_HEAD_BEFORE" = "$PRODUCT_BASE_COMMIT" ] || fail_now "unexpected_product_head" "REVIEW_PRODUCT_REPOSITORY_BEFORE_COMPLETION"
[ "$PRODUCT_REMOTE_BEFORE" = "$PRODUCT_BASE_COMMIT" ] || fail_now "unexpected_product_remote_main" "REVIEW_PRODUCT_REMOTE_BEFORE_COMPLETION"
[ "$PRODUCT_STATUS_BEFORE" = " M README.md" ] || fail_now "unexpected_product_worktree_status" "PRESERVE_ONLY_KNOWN_README_PATCH"
[ -z "$PRODUCT_STAGED_BEFORE" ] || fail_now "unexpected_staged_product_changes" "UNSTAGE_AND_REVIEW_PRODUCT_CHANGES"

if ! git -C "$PRODUCT_REPO" diff --no-ext-diff --unified=0 -- README.md > "$README_PATCH"; then
  fail_now "readme_diff_capture_failed" "INSPECT_PRODUCT_README"
fi
python3 - "$README_PATCH" "$PRODUCT_REPO/README.md" <<'PY_VALIDATE_README'
import sys
from pathlib import Path
patch=Path(sys.argv[1]).read_text(encoding="utf-8",errors="replace")
readme=Path(sys.argv[2]).read_text(encoding="utf-8")
added=[]
deleted=[]
for line in patch.splitlines():
    if line.startswith("+++") or line.startswith("---"):
        continue
    if line.startswith("+"):
        value=line[1:]
        if value.strip():
            added.append(value)
    elif line.startswith("-"):
        value=line[1:]
        if value.strip():
            deleted.append(value)
expected="- `GET /capabilities`"
if deleted:
    raise SystemExit("README patch deletes existing content")
if added != [expected]:
    raise SystemExit(f"unexpected added README lines: {added!r}")
if readme.count(expected) != 1:
    raise SystemExit("README must contain exactly one capabilities API bullet")
api_index=readme.find("## API")
cap_index=readme.find(expected)
if api_index < 0 or cap_index < api_index:
    raise SystemExit("capabilities bullet is not under API section")
PY_VALIDATE_README
[ "$?" -eq 0 ] || fail_now "readme_patch_not_exact_known_gap" "REVIEW_README_PATCH_WITHOUT_COMMITTING"
README_PATCH_VALID="YES"
README_CAPABILITIES_DOCUMENTED="YES"

if [ -x "$PRODUCT_REPO/.venv/bin/python" ]; then
  PYTHON_BIN="$PRODUCT_REPO/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi
log "PYTHON_BIN=$PYTHON_BIN"

if (cd "$PRODUCT_REPO" && "$PYTHON_BIN" -m py_compile app/main.py tests/test_tasks_api.py) >> "$RUN_LOG" 2>&1; then
  PY_COMPILE="PASS"
else
  PY_COMPILE="FAIL"
  fail_now "product_py_compile_failed" "REPAIR_PRODUCT_BEFORE_COMMIT"
fi

if (cd "$PRODUCT_REPO" && "$PYTHON_BIN" -m pytest -q) > "$PYTEST_LOG" 2>&1; then
  PYTEST="PASS"
else
  PYTEST="FAIL"
  cat "$PYTEST_LOG" >> "$RUN_LOG"
  fail_now "product_pytest_failed" "REPAIR_PRODUCT_BEFORE_COMMIT"
fi
cat "$PYTEST_LOG" >> "$RUN_LOG"

if (cd "$PRODUCT_REPO" && "$PYTHON_BIN" - <<'PY_ROUTE'
from app.main import app
routes={(method,path) for route in app.routes for method in getattr(route,"methods",set()) for path in [route.path]}
assert ("GET","/capabilities") in routes
assert ("GET","/health") in routes
assert ("GET","/tasks") in routes
PY_ROUTE
) >> "$RUN_LOG" 2>&1; then
  ROUTE_CONTRACT="PASS"
else
  ROUTE_CONTRACT="FAIL"
  fail_now "product_route_contract_failed" "REPAIR_PRODUCT_BEFORE_COMMIT"
fi

MAIN_HASH_PRECOMMIT="$(sha256sum "$PRODUCT_REPO/app/main.py" | awk '{print $1}')"
TEST_HASH_PRECOMMIT="$(sha256sum "$PRODUCT_REPO/tests/test_tasks_api.py" | awk '{print $1}')"
[ "$MAIN_HASH_PRECOMMIT" = "$MAIN_HASH_BEFORE" ] || fail_now "product_main_changed_during_checks" "RESTORE_PRODUCT_FEATURE_CODE"
[ "$TEST_HASH_PRECOMMIT" = "$TEST_HASH_BEFORE" ] || fail_now "product_tests_changed_during_checks" "RESTORE_PRODUCT_TESTS"
[ "$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all)" = " M README.md" ] || fail_now "product_status_changed_during_checks" "REVIEW_PRODUCT_WORKTREE"

git -C "$PRODUCT_REPO" add -- README.md || fail_now "product_readme_stage_failed" "INSPECT_PRODUCT_GIT_STATE"
STAGED_NAMES="$(git -C "$PRODUCT_REPO" diff --cached --name-only)"
[ "$STAGED_NAMES" = "README.md" ] || fail_now "unexpected_product_staged_files" "UNSTAGE_AND_REVIEW_PRODUCT_CHANGES"
git -C "$PRODUCT_REPO" diff --cached --check >/dev/null 2>&1 || fail_now "product_staged_diff_check_failed" "REPAIR_README_FORMAT"

if ! git -C "$PRODUCT_REPO" commit -m "docs: document capabilities endpoint" >> "$RUN_LOG" 2>&1; then
  git -C "$PRODUCT_REPO" reset README.md >/dev/null 2>&1 || true
  fail_now "product_commit_failed" "INSPECT_PRODUCT_GIT_IDENTITY"
fi
PRODUCT_COMMIT="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_CHANGED_FILES="$(git -C "$PRODUCT_REPO" diff --name-only "$PRODUCT_BASE_COMMIT..$PRODUCT_COMMIT" | paste -sd, -)"
[ "$PRODUCT_CHANGED_FILES" = "README.md" ] || fail_now "product_commit_contains_unexpected_files" "REVIEW_PRODUCT_COMMIT_BEFORE_PUSH"
[ "$(git -C "$PRODUCT_REPO" rev-parse HEAD^ 2>/dev/null)" = "$PRODUCT_BASE_COMMIT" ] || fail_now "product_commit_parent_mismatch" "REVIEW_PRODUCT_COMMIT_BEFORE_PUSH"

if ! git -C "$PRODUCT_REPO" push origin HEAD:main >> "$RUN_LOG" 2>&1; then
  fail_now "product_push_failed" "RETRY_CONTROLLED_PRODUCT_PUSH_AFTER_REMOTE_REVIEW"
fi
PRODUCT_REMOTE_MAIN="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ -n "$PRODUCT_COMMIT" ] && [ "$PRODUCT_REMOTE_MAIN" = "$PRODUCT_COMMIT" ]; then
  PRODUCT_SHA_VERIFIED="YES"
else
  fail_now "product_remote_sha_mismatch" "VERIFY_PRODUCT_REMOTE_MAIN"
fi

PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
if [ -z "$PRODUCT_STATUS_AFTER" ]; then PRODUCT_WORKTREE_CLEAN="YES"; else fail_now "product_worktree_not_clean_after_push" "INSPECT_PRODUCT_WORKTREE"; fi
REMOTE_README="$TMP_ROOT/remote-readme.md"
git -C "$PRODUCT_REPO" show "$PRODUCT_REMOTE_MAIN:README.md" > "$REMOTE_README" 2>> "$RUN_LOG" || fail_now "remote_readme_read_failed" "VERIFY_PRODUCT_REMOTE_CONTENT"
[ "$(grep -Fxc -- '- `GET /capabilities`' "$REMOTE_README" || true)" = "1" ] || fail_now "remote_readme_missing_capabilities" "VERIFY_PRODUCT_REMOTE_CONTENT"

MAIN_HASH_AFTER="$(sha256sum "$PRODUCT_REPO/app/main.py" | awk '{print $1}')"
TEST_HASH_AFTER="$(sha256sum "$PRODUCT_REPO/tests/test_tasks_api.py" | awk '{print $1}')"
[ "$MAIN_HASH_AFTER" = "$MAIN_HASH_BEFORE" ] || fail_now "product_feature_code_mutated" "RESTORE_PRODUCT_FEATURE_CODE"
[ "$TEST_HASH_AFTER" = "$TEST_HASH_BEFORE" ] || fail_now "product_tests_mutated" "RESTORE_PRODUCT_TESTS"

RESULT="COMPLETED"
NEXT_ACTION="DISCOVER_STABLE_OPENCLAW_TOOL_ACTION_PLUGIN_CONTRACT_AND_ESTABLISH_RESPONSE_LATENCY_BASELINE"

export TASK_ID PRODUCT_TASK_ID PRODUCT_BASE_COMMIT PRODUCT_COMMIT PRODUCT_REMOTE_MAIN PRODUCT_CHANGED_FILES SUPPLEMENTAL_ACCEPTANCE_COMMIT SUPPLEMENTAL_ACCEPTANCE_JSON STAMP ISO_TIME RESULT FAILURE_CODE ACTIVE_QUEUE_COUNT README_PATCH_VALID README_CAPABILITIES_DOCUMENTED PY_COMPILE PYTEST ROUTE_CONTRACT PRODUCT_SHA_VERIFIED PRODUCT_WORKTREE_CLEAN NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL COMPLETION_DOC_REL CURRENT_STATE_REL HANDOFF_REL
python3 - "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path
payload={
  "task_id":os.environ["TASK_ID"],
  "product_task_id":os.environ["PRODUCT_TASK_ID"],
  "checked_at":os.environ["ISO_TIME"],
  "result":os.environ["RESULT"],
  "failure_code":os.environ.get("FAILURE_CODE","") or None,
  "native_openclaw_acceptance":{
    "supplemental_acceptance_commit":os.environ["SUPPLEMENTAL_ACCEPTANCE_COMMIT"],
    "supplemental_acceptance_json":os.environ["SUPPLEMENTAL_ACCEPTANCE_JSON"],
    "final_acceptance":"PASS",
    "session_delete_verified":True,
    "first_session_preserved":True,
    "latency_runtime_ms_available":False,
  },
  "product":{
    "repository":"ShanGouXueHui/oris-final-acceptance-api",
    "base_commit":os.environ["PRODUCT_BASE_COMMIT"],
    "final_commit":os.environ["PRODUCT_COMMIT"],
    "remote_main":os.environ["PRODUCT_REMOTE_MAIN"],
    "sha_verified":os.environ["PRODUCT_SHA_VERIFIED"]=="YES",
    "worktree_clean":os.environ["PRODUCT_WORKTREE_CLEAN"]=="YES",
    "changed_files":[x for x in os.environ.get("PRODUCT_CHANGED_FILES","").split(",") if x],
    "readme_patch_valid":os.environ["README_PATCH_VALID"]=="YES",
    "readme_capabilities_documented":os.environ["README_CAPABILITIES_DOCUMENTED"]=="YES",
    "py_compile":os.environ["PY_COMPILE"],
    "pytest":os.environ["PYTEST"],
    "route_contract":os.environ["ROUTE_CONTRACT"],
  },
  "safety":{
    "active_queue_count":int(os.environ["ACTIVE_QUEUE_COUNT"]),
    "new_product_task_submitted":False,
    "product_feature_code_mutated":False,
    "openclaw_config_mutated":False,
    "nginx_changed":False,
    "secret_values_recorded":False,
  },
  "persistent_context":{
    "completion_doc":os.environ["COMPLETION_DOC_REL"],
    "current_state":os.environ["CURRENT_STATE_REL"],
    "next_chat_handoff":os.environ["HANDOFF_REL"],
    "current_task_updated":True,
  },
  "next_action":os.environ["NEXT_ACTION"],
  "evidence":{
    "log_path":os.environ["EVIDENCE_LOG_REL"],
    "json_path":os.environ["EVIDENCE_JSON_REL"],
    "self_commit_sha_omitted_to_prevent_post_commit_log_drift":True,
  },
}
Path(sys.argv[1]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_RESULT

{
  echo "PRODUCT_COMMIT=$PRODUCT_COMMIT"
  echo "PRODUCT_REMOTE_MAIN=$PRODUCT_REMOTE_MAIN"
  echo "PRODUCT_SHA_VERIFIED=$PRODUCT_SHA_VERIFIED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "PRODUCT_CHANGED_FILES=$PRODUCT_CHANGED_FILES"
  echo "README_PATCH_VALID=$README_PATCH_VALID"
  echo "README_CAPABILITIES_DOCUMENTED=$README_CAPABILITIES_DOCUMENTED"
  echo "PY_COMPILE=$PY_COMPILE"
  echo "PYTEST=$PYTEST"
  echo "ROUTE_CONTRACT=$ROUTE_CONTRACT"
  echo "PERSISTENT_CONTEXT_UPDATE_PLANNED=YES"
  echo "SECRET_VALUES_RECORDED=NO"
} >> "$RUN_LOG"

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY_SECRET_SCAN'
import re,sys
from pathlib import Path
patterns=[
 re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
 re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
 re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
 re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
 re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
 re.compile(r"(?i)(password|authorization|credential|gateway[_ -]?token)(\s*[=:]\s*|\s+)(?!<redacted>|true\b|false\b|yes\b|no\b|null\b|unchanged\b)[A-Za-z0-9._~+/-]{20,}"),
]
for filename in sys.argv[1:]:
    text=Path(filename).read_text(encoding="utf-8",errors="replace")
    if any(pattern.search(text) for pattern in patterns):
        raise SystemExit(1)
PY_SECRET_SCAN
if [ "$?" -eq 0 ]; then SECRET_SCAN="PASS"; else fail_now "completion_evidence_secret_scan_failed" "REPAIR_COMPLETION_EVIDENCE_REDACTION"; fi

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "oris_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL" "$WORKTREE/memory/dev_employee" || fail_now "oris_evidence_directory_create_failed" "CHECK_ORIS_WORKTREE_PERMISSIONS"

python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_COPY_EVIDENCE'
import json,sys
from pathlib import Path
sl,dl,sj,dj=map(Path,sys.argv[1:])
dl.write_text("\n".join(line.rstrip(" \t\r") for line in sl.read_text(encoding="utf-8",errors="replace").splitlines())+"\n",encoding="utf-8")
dj.write_text(json.dumps(json.loads(sj.read_text(encoding="utf-8")),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_COPY_EVIDENCE

python3 - "$WORKTREE/$CURRENT_TASK_JSON_REL" "$PRODUCT_COMMIT" "$PRODUCT_REMOTE_MAIN" "$EVIDENCE_JSON_REL" "$ISO_TIME" <<'PY_UPDATE_TASK_JSON'
import json,sys
from pathlib import Path
path=Path(sys.argv[1]); product_commit=sys.argv[2]; remote_main=sys.argv[3]; evidence_json=sys.argv[4]; now=sys.argv[5]
data=json.loads(path.read_text(encoding="utf-8"))
if data.get("task_id") != "commercial-native-openclaw-ui-20260617":
    raise SystemExit("unexpected current task id")
data["status"]="completed"
data["current_step"]="native_openclaw_ui_and_product_readme_completion_verified"
data["diagnosis"]["current_root_ui_is_native_openclaw"]=True
data["diagnosis"]["current_root_ui"]="native OpenClaw Gateway UI"
data["diagnosis"]["missing_standard_features"]=[]
data["diagnosis"]["decision"]="native OpenClaw UI accepted as primary; custom ORIS shell retained only on restricted diagnostic/rollback routes"
completed=data["completed_real_task"]
completed["product_commit"]=product_commit
completed["product_remote_main"]=remote_main
completed["acceptance_gap"]="repaired: README API list now documents GET /capabilities"
completed["final_acceptance"]="complete; implementation, tests, README, product commit/push, remote SHA and ORIS evidence verified"
data["completion"]={
  "native_openclaw_ui_acceptance":"PASS",
  "session_delete_verified":True,
  "first_session_preserved":True,
  "public_root":"native OpenClaw Gateway UI",
  "admin_route":"restricted ORIS Web Console",
  "rollback_route":"restricted custom ORIS chat shell",
  "authentication_mode":"token",
  "control_ui_device_pairing_bypass":True,
  "product_final_commit":product_commit,
  "product_remote_main":remote_main,
  "completion_evidence_json":evidence_json,
  "latency_observation":"exact runtimeMs unavailable in current session CLI output; establish a dedicated response-latency baseline next",
}
data["platform_state"]["active_product_task"]=False
data["next_action"]="Discover and implement the stable OpenClaw tools/actions/plugin contract for ORIS, and establish response-latency observability before broader commercial rollout. Do not reopen the completed acceptance task without regression evidence."
data["last_error"]=""
data["blocked_reason"]=""
data["updated_at"]=now
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_UPDATE_TASK_JSON
[ "$?" -eq 0 ] || fail_now "current_task_json_update_failed" "INSPECT_CURRENT_TASK_CONTEXT"

cat > "$WORKTREE/$CURRENT_TASK_MD_REL" <<EOF_CURRENT_TASK
# Current AI Dev Employee Task

Status: completed

Task id: \`$TASK_ID\`

Completion time: \`$ISO_TIME\`

## Final result

The native OpenClaw Gateway UI is now the primary commercial conversation interface at \`https://control.orisfy.com\`.

Accepted chain:

\`human → native OpenClaw UI → Agent Harness tool/policy adapter → ORIS control plane → Codex executor → product/evidence back to OpenClaw\`

Final browser acceptance: \`PASS\`.

Verified native behaviors:

- token-authenticated connection;
- new conversation;
- multiple independent conversations;
- history visibility and switching;
- refresh persistence;
- session-level deletion with the first conversation preserved;
- restricted \`/admin\` loading;
- restricted \`/_oris-chat-shell\` rollback/diagnostic route loading.

The earlier acceptance record that incorrectly marked session deletion as tested is superseded by:

\`$SUPPLEMENTAL_ACCEPTANCE_JSON\`

Evidence commit: \`$SUPPLEMENTAL_ACCEPTANCE_COMMIT\`.

## Runtime and security state

- OpenClaw Gateway remains the existing installation on \`127.0.0.1:18789\`;
- OpenClaw was not reinstalled or upgraded;
- Nginx root routes to native OpenClaw;
- \`/admin\` routes to the ORIS Web Console and remains restricted;
- \`/_oris-chat-shell\` remains a restricted rollback route;
- intake on \`127.0.0.1:18892\` is not publicly exposed;
- Gateway auth mode is token;
- Control UI device pairing is intentionally bypassed for all clients holding a valid Gateway credential through \`gateway.controlUi.dangerouslyDisableDeviceAuth=true\`;
- this pairing bypass is a conscious commercial-security exception and does not disable token authentication.

## Controlled product task completion

Task: \`$PRODUCT_TASK_ID\`

Product repository: \`$PRODUCT_REMOTE_REPO\`

Base implementation commit: \`$PRODUCT_BASE_COMMIT\`

Final product commit: \`$PRODUCT_COMMIT\`

Remote main: \`$PRODUCT_REMOTE_MAIN\`

Verified:

- \`GET /capabilities\` implementation remains unchanged;
- existing pytest coverage passes;
- \`README.md\` API list now includes \`GET /capabilities\`;
- the completion commit changes only \`README.md\`;
- local HEAD and remote main match;
- product worktree is clean.

## Open item that does not block acceptance

The current \`openclaw sessions --json\` output did not expose usable \`runtimeMs\` samples for the browser conversations. Exact response latency therefore remains unmeasured. Functional acceptance is complete, but commercial rollout requires dedicated time-to-first-token and total-response latency observability.

## Next action

Do not submit or rerun the completed acceptance task.

Proceed with:

1. discovery of the stable OpenClaw tools/actions/plugin interface supported by the installed version;
2. generic ORIS action exposure through that interface, without broad prompt-keyword matching;
3. response-latency baseline and observability;
4. regression checks for native UI, authentication, Nginx routing and restricted diagnostic routes.
EOF_CURRENT_TASK

cat > "$WORKTREE/$COMPLETION_DOC_REL" <<EOF_COMPLETION
# ORIS Dev Employee — Native OpenClaw Commercial UI Completion

Date: 2026-06-17

## Final result

Status: \`PASS\`

The public primary interface is the native OpenClaw Gateway UI. The custom ORIS Web Console is no longer the default commercial chat shell.

## Accepted architecture

\`human → native OpenClaw UI → Agent Harness tool/policy adapter → ORIS task governance → Codex execution → product/test/evidence returned through OpenClaw\`

## Native UI evidence

- automated Nginx and route preflight: PASS;
- token authentication: PASS;
- new and second conversation: PASS;
- history and switching: PASS;
- refresh persistence: PASS;
- session-level deletion: PASS;
- first conversation preserved after second-session deletion: PASS;
- \`/admin\` restricted and loads after authentication: PASS;
- \`/_oris-chat-shell\` restricted and loads after authentication: PASS;
- intake loopback-only: PASS;
- authoritative supplemental evidence: \`$SUPPLEMENTAL_ACCEPTANCE_JSON\`;
- supplemental evidence commit: \`$SUPPLEMENTAL_ACCEPTANCE_COMMIT\`.

## Product gap closure

- controlled task: \`$PRODUCT_TASK_ID\`;
- product repository: \`$PRODUCT_REMOTE_REPO\`;
- base feature commit: \`$PRODUCT_BASE_COMMIT\`;
- final documentation commit: \`$PRODUCT_COMMIT\`;
- product remote main: \`$PRODUCT_REMOTE_MAIN\`;
- README API list includes \`GET /capabilities\`: PASS;
- py_compile: PASS;
- pytest: PASS;
- route contract: PASS;
- completion diff limited to \`README.md\`: PASS;
- product worktree clean: PASS;
- product SHA equals remote SHA: PASS.

## Security and operational exceptions

OpenClaw authentication remains token-based. Control UI device pairing is intentionally bypassed through \`gateway.controlUi.dangerouslyDisableDeviceAuth=true\` so any browser with a valid Gateway credential can connect without per-device approval. This setting is an explicit risk acceptance and must remain documented in future security reviews.

## Latency status

The browser screenshot only showed minute-level timestamps, and the installed version's session CLI returned no usable \`runtimeMs\` samples for these conversations. No numerical latency claim is accepted. Dedicated TTFT and total-response telemetry is the next observability requirement.

## Operational conclusion

The migration and the previously partial product task are complete. Do not rerun either acceptance task unless regression evidence shows failure.
EOF_COMPLETION

cat > "$WORKTREE/$CURRENT_STATE_REL" <<EOF_STATE
# ORIS Dev Employee — Current State After Native OpenClaw Completion

Date: 2026-06-17

This file supersedes pending-migration statements in earlier 2026-06-17 state and handoff documents.

## Current production-facing state

- public root: native OpenClaw Gateway UI;
- Gateway: existing service on \`127.0.0.1:18789\`;
- ORIS Web Console: restricted at \`/admin\`, upstream \`127.0.0.1:18893\`;
- custom ORIS chat shell: restricted rollback/diagnostic route \`/_oris-chat-shell\`;
- intake: loopback-only on \`127.0.0.1:18892\`;
- Nginx duplicate server blocks: removed;
- OpenClaw auth: token;
- Control UI device pairing: bypassed for clients with valid token;
- active product task: none.

## Completed task

\`$TASK_ID\` is complete.

The controlled product task \`$PRODUCT_TASK_ID\` is also fully complete after the README repair.

Final product SHA: \`$PRODUCT_COMMIT\`.

## Next commercial priority

1. discover the stable tools/actions/plugin contract in the installed OpenClaw version;
2. expose generic ORIS actions through that contract;
3. eliminate broad keyword-based task creation from the primary path;
4. establish TTFT and total-response latency telemetry;
5. preserve rollback, authentication, audit and evidence guarantees.
EOF_STATE

cat > "$WORKTREE/$HANDOFF_REL" <<EOF_HANDOFF
# Next Chat Handoff — Native OpenClaw UI Completed

Date: 2026-06-17

Read this file before the older \`NEXT_CHAT_HANDOFF_2026-06-17.md\` when continuing the project.

## Completed

- native OpenClaw is the primary public UI;
- browser acceptance including session-level deletion passed;
- token authentication remains enabled;
- device pairing is intentionally bypassed for authenticated Control UI clients;
- \`/admin\` and \`/_oris-chat-shell\` remain restricted;
- intake remains loopback-only;
- product README gap for \`GET /capabilities\` is repaired;
- product tests, commit, push and remote SHA are verified;
- current commercial migration task is closed.

## Do not do

- do not reinstall or upgrade OpenClaw as part of continuation;
- do not restore the custom shell as the default UI;
- do not submit another acceptance task;
- do not use broad prompt keyword matching as the primary task-creation mechanism;
- do not claim a latency number until dedicated telemetry exists.

## Continue with

Read-only discovery first, then implement the smallest stable OpenClaw tool/action/plugin adapter that exposes ORIS task governance while keeping Codex as executor. In parallel, add response-latency observability with TTFT and total completion duration.
EOF_HANDOFF

python3 - "$WORKTREE/$CONTEXT_INDEX_REL" <<'PY_UPDATE_INDEX'
from pathlib import Path
path=Path(__import__('sys').argv[1])
text=path.read_text(encoding='utf-8')
marker='## Mandatory read order\n\n'
insert=(
 '## Mandatory read order\n\n'
 'Superseding completion files — read these first:\n\n'
 '- `memory/dev_employee/CURRENT_STATE_2026-06-17_NATIVE_UI_COMPLETED.md`\n'
 '- `memory/dev_employee/current_task.json`\n'
 '- `memory/dev_employee/current_task.md`\n'
 '- `memory/dev_employee/COMMERCIAL_NATIVE_OPENCLAW_UI_COMPLETION_2026-06-17.md`\n'
 '- `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-17_NATIVE_UI_COMPLETED.md`\n\n'
 'Then use the historical numbered order for background:\n\n'
)
if 'CURRENT_STATE_2026-06-17_NATIVE_UI_COMPLETED.md' not in text:
    if marker not in text:
        raise SystemExit('mandatory read marker missing')
    text=text.replace(marker,insert,1)
text=text.replace('`native_openclaw_ui_switch_pending`','`completed`',1)
old_action=(
 '- read-only discover native OpenClaw UI, WebSocket, auth/pairing, session/history capabilities and effective Nginx routing;\n'
 '- commit sanitized discovery evidence;\n'
 '- then build a reversible root-route migration;\n'
 '- do not submit another product task before browser acceptance.'
)
new_action=(
 '- native OpenClaw root migration and browser acceptance are complete;\n'
 '- the missing product README update is committed and remote-verified;\n'
 '- next discover stable OpenClaw tools/actions/plugins and establish latency observability;\n'
 '- do not rerun completed acceptance tasks without regression evidence.'
)
if old_action in text:
    text=text.replace(old_action,new_action,1)
old_gap='Implemented `/capabilities` and tests, but omitted the explicitly requested README API-list update. Treat as partially delivered until repaired and fully re-verified.'
new_gap='Implemented `/capabilities` and tests. The README API-list gap has now been repaired, tested, committed, pushed and remote-SHA verified. Treat this controlled product task as fully complete.'
if old_gap in text:
    text=text.replace(old_gap,new_gap,1)
path.write_text(text,encoding='utf-8')
PY_UPDATE_INDEX
[ "$?" -eq 0 ] || fail_now "context_index_update_failed" "INSPECT_CONTEXT_INDEX"

python3 - "$WORKTREE/$CURRENT_TASK_JSON_REL" "$WORKTREE/$COMPLETION_DOC_REL" "$WORKTREE/$CURRENT_STATE_REL" "$WORKTREE/$HANDOFF_REL" <<'PY_VALIDATE_CONTEXT'
import json,sys
from pathlib import Path
task=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
assert task['status']=='completed'
assert task['completion']['native_openclaw_ui_acceptance']=='PASS'
assert task['completed_real_task']['product_commit']==task['completed_real_task']['product_remote_main']
for item in sys.argv[2:]:
    text=Path(item).read_text(encoding='utf-8')
    assert len(text)>200
PY_VALIDATE_CONTEXT
[ "$?" -eq 0 ] || fail_now "persistent_context_validation_failed" "INSPECT_PERSISTENT_CONTEXT_FILES"
ORIS_CONTEXT_UPDATED="YES"

git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" "$CURRENT_TASK_JSON_REL" "$CURRENT_TASK_MD_REL" "$CONTEXT_INDEX_REL" "$COMPLETION_DOC_REL" "$CURRENT_STATE_REL" "$HANDOFF_REL" || fail_now "oris_evidence_git_add_failed" "INSPECT_ORIS_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "oris_evidence_diff_check_failed" "REPAIR_ORIS_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): complete native OpenClaw commercial migration" >/dev/null 2>&1 || fail_now "oris_evidence_commit_failed" "INSPECT_ORIS_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "oris_evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "oris_evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "oris_evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
ORIS_REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ -n "$EVIDENCE_COMMIT" ] && [ "$ORIS_REMOTE_MAIN" = "$EVIDENCE_COMMIT" ]; then
  EVIDENCE_REMOTE_VERIFIED="YES"
else
  RESULT="FAILED"
  FAILURE_CODE="oris_evidence_remote_sha_mismatch"
  NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"
fi

summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
