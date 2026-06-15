#!/usr/bin/env bash

ORIS_DIR="/home/admin/projects/oris"
CODEX_BIN="/home/admin/.npm-global/bin/codex"
WORKDIR="/home/admin/projects"
BRIDGE_SERVICE="oris-dev-employee-bridge.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
WEB_SERVICE="oris-dev-employee-web-console.service"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_DIR="$ORIS_DIR/logs/dev_employee/codex_auth_preflight"
RUN_LOG="$LOG_DIR/resume-codex-auth-$STAMP.log"
ADMIN_LOG="$LOG_DIR/admin-preflight-$STAMP.json"
SYSTEMD_LOG="$LOG_DIR/bridge-context-preflight-$STAMP.json"
TMP_OUTPUT="/tmp/oris-codex-auth-resume-$STAMP.out"

RESULT="FAILED"
PATCH_RESULT="NOT_RUN"
TEST_RESULT="NOT_RUN"
HARDENING_COMMIT=""
ADMIN_PREFLIGHT="NOT_RUN"
SYSTEMD_PREFLIGHT="NOT_RUN"
BRIDGE_CONTEXT="NOT_VERIFIED"
FAILURE_CODE=""
LOG_COMMIT=""
NEXT_ACTION="INSPECT_GITHUB_LOG"

mkdir -p "$LOG_DIR"

log_line() {
  printf '%s\n' "$*" >> "$RUN_LOG"
}

json_field() {
  local file="$1"
  local field="$2"
  python3 - "$file" "$field" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
field = sys.argv[2]
try:
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get(field)
    if isinstance(value, bool):
        print("true" if value else "false")
    elif value is None:
        print("")
    else:
        print(value)
except Exception:
    print("")
PY
}

commit_logs() {
  cd "$ORIS_DIR" || return 1
  git add "$RUN_LOG" 2>/dev/null || true
  [ -f "$ADMIN_LOG" ] && git add "$ADMIN_LOG" 2>/dev/null || true
  [ -f "$SYSTEMD_LOG" ] && git add "$SYSTEMD_LOG" 2>/dev/null || true
  if git diff --cached --quiet; then
    LOG_COMMIT="NO_LOG_CHANGES"
    return 0
  fi
  git commit -m "test(dev-employee): record resumed Codex auth preflight $STAMP" > "$TMP_OUTPUT" 2>&1
  if [ "$?" -ne 0 ]; then
    LOG_COMMIT="LOG_COMMIT_FAILED"
    return 1
  fi
  git push origin main > "$TMP_OUTPUT" 2>&1
  if [ "$?" -ne 0 ]; then
    LOG_COMMIT="LOG_PUSH_FAILED"
    return 1
  fi
  LOG_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  return 0
}

print_summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "PATCH_RESULT=$PATCH_RESULT"
  echo "TEST_RESULT=$TEST_RESULT"
  echo "CODE_HARDENING_COMMIT=$HARDENING_COMMIT"
  echo "ADMIN_CODEX_PREFLIGHT=$ADMIN_PREFLIGHT"
  echo "SYSTEMD_CODEX_PREFLIGHT=$SYSTEMD_PREFLIGHT"
  echo "BRIDGE_AUTH_CONTEXT=$BRIDGE_CONTEXT"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "BRIDGE_SERVICE=$(systemctl --user is-active "$BRIDGE_SERVICE" 2>/dev/null || true)"
  echo "INTAKE_SERVICE=$(systemctl --user is-active "$INTAKE_SERVICE" 2>/dev/null || true)"
  echo "WEB_CONSOLE_SERVICE=$(systemctl --user is-active "$WEB_SERVICE" 2>/dev/null || true)"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail_and_finish() {
  RESULT="FAILED"
  NEXT_ACTION="$1"
  log_line "RESULT=FAILED"
  log_line "FAILURE_CODE=$FAILURE_CODE"
  log_line "NEXT_ACTION=$NEXT_ACTION"
  commit_logs || true
  print_summary
  rm -f "$TMP_OUTPUT"
  exit 1
}

if [ "$(id -un)" != "admin" ]; then
  FAILURE_CODE="wrong_linux_user"
  NEXT_ACTION="RUN_AS_ADMIN"
  print_summary
  exit 1
fi

cd "$ORIS_DIR" || {
  echo "ORIS_DIR_NOT_FOUND"
  exit 1
}

{
  echo "===== timestamp ====="
  date -Is
  echo
  echo "===== execution identity ====="
  echo "linux_user=$(id -un)"
  echo "uid=$(id -u)"
  echo "home=$HOME"
  echo
  echo "===== starting git state ====="
  git rev-parse HEAD
  git status --short
} > "$RUN_LOG" 2>&1

systemctl --user stop "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1
if [ "$(systemctl --user is-active "$BRIDGE_SERVICE" 2>/dev/null || true)" = "active" ]; then
  FAILURE_CODE="bridge_stop_failed"
  fail_and_finish "INSPECT_BRIDGE_SERVICE"
fi
log_line "bridge_stopped=true"

python3 scripts/dev_employee_apply_auth_terminal_hardening_20260616.py >> "$RUN_LOG" 2>&1
if [ "$?" -ne 0 ]; then
  FAILURE_CODE="hardening_patch_failed"
  fail_and_finish "INSPECT_HARDENING_PATCH_LOG"
fi
PATCH_RESULT="PASS"

python3 -m py_compile \
  scripts/dev_employee_task_states.py \
  scripts/dev_employee_codex_auth_preflight.py \
  scripts/dev_employee_apply_auth_terminal_hardening_20260616.py \
  scripts/dev_employee_supervised_bridge_v2.py \
  scripts/dev_employee_intake_api.py >> "$RUN_LOG" 2>&1
if [ "$?" -ne 0 ]; then
  FAILURE_CODE="python_compile_failed"
  fail_and_finish "FIX_PLATFORM_STATIC_CHECKS"
fi

bash -n scripts/dev_employee_finish_public_web_submit_e2e.sh >> "$RUN_LOG" 2>&1
if [ "$?" -ne 0 ]; then
  FAILURE_CODE="finisher_shell_syntax_failed"
  fail_and_finish "FIX_FINISHER_SYNTAX"
fi

PYTHONPATH="$ORIS_DIR" python3 tests/test_dev_employee_task_states.py >> "$RUN_LOG" 2>&1
STATE_TEST_RC="$?"
PYTHONPATH="$ORIS_DIR" python3 tests/test_dev_employee_codex_auth_preflight.py >> "$RUN_LOG" 2>&1
AUTH_TEST_RC="$?"
if [ "$STATE_TEST_RC" -ne 0 ] || [ "$AUTH_TEST_RC" -ne 0 ]; then
  FAILURE_CODE="platform_regression_tests_failed"
  fail_and_finish "FIX_PLATFORM_REGRESSION_TESTS"
fi

git diff --check >> "$RUN_LOG" 2>&1
if [ "$?" -ne 0 ]; then
  FAILURE_CODE="git_diff_check_failed"
  fail_and_finish "FIX_PLATFORM_DIFF"
fi
TEST_RESULT="PASS"

# Stage only the authoritative runtime changes. Existing unrelated dirty files stay untouched.
git add \
  scripts/dev_employee_supervised_bridge_v2.py \
  scripts/dev_employee_intake_api.py \
  scripts/dev_employee_finish_public_web_submit_e2e.sh >> "$RUN_LOG" 2>&1
if [ "$?" -ne 0 ]; then
  FAILURE_CODE="git_add_failed"
  fail_and_finish "INSPECT_GIT_STATE"
fi

if git diff --cached --quiet; then
  HARDENING_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  log_line "hardening_commit_created=false"
else
  git commit -m "fix(dev-employee): gate Codex auth and terminate failed tasks" >> "$RUN_LOG" 2>&1
  if [ "$?" -ne 0 ]; then
    FAILURE_CODE="hardening_commit_failed"
    fail_and_finish "INSPECT_GIT_COMMIT_LOG"
  fi
  HARDENING_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  git push origin main >> "$RUN_LOG" 2>&1
  if [ "$?" -ne 0 ]; then
    FAILURE_CODE="hardening_push_failed"
    fail_and_finish "RESOLVE_ORIS_GIT_PUSH"
  fi
fi

REMOTE_SHA="$(git ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
if [ -z "$HARDENING_COMMIT" ] || [ "$REMOTE_SHA" != "$HARDENING_COMMIT" ]; then
  FAILURE_CODE="hardening_remote_sha_mismatch"
  fail_and_finish "RESOLVE_ORIS_REMOTE_SHA"
fi

systemctl --user restart "$INTAKE_SERVICE" >> "$RUN_LOG" 2>&1
if [ "$?" -ne 0 ]; then
  FAILURE_CODE="intake_restart_failed"
  fail_and_finish "INSPECT_INTAKE_SERVICE"
fi
systemctl --user restart "$WEB_SERVICE" >> "$RUN_LOG" 2>&1
if [ "$?" -ne 0 ]; then
  FAILURE_CODE="web_console_restart_failed"
  fail_and_finish "INSPECT_WEB_CONSOLE_SERVICE"
fi

if [ ! -x "$CODEX_BIN" ]; then
  FAILURE_CODE="codex_executable_missing"
  fail_and_finish "RESTORE_CODEX_INSTALLATION"
fi

"$CODEX_BIN" --version >> "$RUN_LOG" 2>&1
if [ "$?" -ne 0 ]; then
  FAILURE_CODE="codex_version_failed"
  fail_and_finish "RESTORE_CODEX_INSTALLATION"
fi

python3 scripts/dev_employee_codex_auth_preflight.py \
  --codex-bin "$CODEX_BIN" \
  --workdir "$WORKDIR" \
  --log "$ADMIN_LOG" \
  --timeout 120 > "$TMP_OUTPUT" 2>&1
ADMIN_RC="$?"
cat "$TMP_OUTPUT" >> "$RUN_LOG"
FAILURE_CODE="$(json_field "$ADMIN_LOG" failure_code)"

if [ "$ADMIN_RC" -ne 0 ]; then
  ADMIN_PREFLIGHT="FAILED"
  if [ "$FAILURE_CODE" != "codex_authentication" ]; then
    fail_and_finish "INSPECT_CODEX_PREFLIGHT_LOG"
  fi

  echo
  echo "Codex 登录已失效。下面在当前 admin 终端重新登录；认证内容不会写入 GitHub 日志。"
  "$CODEX_BIN" logout >/dev/null 2>&1 || true
  if "$CODEX_BIN" login --help 2>&1 | grep -q -- "--device-auth"; then
    "$CODEX_BIN" login --device-auth
  else
    "$CODEX_BIN" login
  fi
  if [ "$?" -ne 0 ]; then
    FAILURE_CODE="codex_login_failed"
    fail_and_finish "COMPLETE_CODEX_LOGIN_AND_RERUN_RESUME_SCRIPT"
  fi
fi

python3 scripts/dev_employee_codex_auth_preflight.py \
  --codex-bin "$CODEX_BIN" \
  --workdir "$WORKDIR" \
  --log "$ADMIN_LOG" \
  --timeout 120 > "$TMP_OUTPUT" 2>&1
ADMIN_RC="$?"
cat "$TMP_OUTPUT" >> "$RUN_LOG"
if [ "$ADMIN_RC" -ne 0 ]; then
  ADMIN_PREFLIGHT="FAILED"
  FAILURE_CODE="$(json_field "$ADMIN_LOG" failure_code)"
  fail_and_finish "COMPLETE_CODEX_LOGIN_AND_RERUN_RESUME_SCRIPT"
fi
ADMIN_PREFLIGHT="PASS"
FAILURE_CODE=""

UNIT_NAME="oris-codex-auth-preflight-$STAMP"
systemd-run --user --wait --collect --pipe \
  --unit="$UNIT_NAME" \
  /usr/bin/python3 "$ORIS_DIR/scripts/dev_employee_codex_auth_preflight.py" \
  --codex-bin "$CODEX_BIN" \
  --workdir "$WORKDIR" \
  --log "$SYSTEMD_LOG" \
  --timeout 120 > "$TMP_OUTPUT" 2>&1
SYSTEMD_RC="$?"
cat "$TMP_OUTPUT" >> "$RUN_LOG"
if [ "$SYSTEMD_RC" -ne 0 ]; then
  SYSTEMD_PREFLIGHT="FAILED"
  BRIDGE_CONTEXT="FAILED"
  FAILURE_CODE="$(json_field "$SYSTEMD_LOG" failure_code)"
  fail_and_finish "ALIGN_BRIDGE_CODEX_AUTH_CONTEXT"
fi

SYSTEMD_OK="$(json_field "$SYSTEMD_LOG" ok)"
SYSTEMD_USER="$(json_field "$SYSTEMD_LOG" linux_user)"
SYSTEMD_HOME="$(json_field "$SYSTEMD_LOG" home)"
if [ "$SYSTEMD_OK" != "true" ] || [ "$SYSTEMD_USER" != "admin" ] || [ "$SYSTEMD_HOME" != "/home/admin" ]; then
  SYSTEMD_PREFLIGHT="FAILED"
  BRIDGE_CONTEXT="FAILED"
  FAILURE_CODE="bridge_auth_context_mismatch"
  fail_and_finish "ALIGN_BRIDGE_CODEX_AUTH_CONTEXT"
fi
SYSTEMD_PREFLIGHT="PASS"
BRIDGE_CONTEXT="PASS"

systemctl --user restart "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1
if [ "$?" -ne 0 ]; then
  FAILURE_CODE="bridge_restart_failed"
  fail_and_finish "INSPECT_BRIDGE_SERVICE"
fi
sleep 2
if [ "$(systemctl --user is-active "$BRIDGE_SERVICE" 2>/dev/null || true)" != "active" ]; then
  FAILURE_CODE="bridge_not_active"
  fail_and_finish "INSPECT_BRIDGE_SERVICE"
fi

log_line "stdlib_regression_tests=PASS"
log_line "admin_preflight=PASS"
log_line "systemd_preflight=PASS"
log_line "bridge_auth_context=PASS"
log_line "real_product_task_submitted=NO"

RESULT="PASS"
NEXT_ACTION="SUBMIT_NEW_PUBLIC_WEB_READONLY_E2E_TASK"
commit_logs || {
  RESULT="FAILED"
  FAILURE_CODE="auth_evidence_push_failed"
  NEXT_ACTION="RESOLVE_ORIS_EVIDENCE_PUSH"
}
print_summary
rm -f "$TMP_OUTPUT"

if [ "$RESULT" = "PASS" ]; then
  exit 0
fi
exit 1
