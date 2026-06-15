#!/usr/bin/env bash

ORIS_DIR="/home/admin/projects/oris"
CODEX_BIN="/home/admin/.npm-global/bin/codex"
WORKDIR="/home/admin/projects"
BRIDGE_SERVICE="oris-dev-employee-bridge.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
WEB_SERVICE="oris-dev-employee-web-console.service"
HARDENING_COMMIT="57cf6eccb1bbf7cc4e6ddd79eab94e7530d3fe5c"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_DIR="$ORIS_DIR/logs/dev_employee/codex_auth_preflight"
RUN_LOG="$LOG_DIR/complete-device-login-$STAMP.log"
ADMIN_LOG="$LOG_DIR/admin-preflight-$STAMP.json"
SYSTEMD_LOG="$LOG_DIR/bridge-context-preflight-$STAMP.json"
LOGIN_DIAGNOSTIC="$LOG_DIR/login-diagnostic-$STAMP.json"
TMP_OUTPUT="/tmp/oris-codex-login-complete-$STAMP.out"

RESULT="FAILED"
DEVICE_AUTH_LOGIN="NOT_RUN"
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

write_login_diagnostic() {
  python3 - "$HOME" "$LOGIN_DIAGNOSTIC" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

home = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])
candidates = sorted(
    home.glob(".codex/**/codex-login.log"),
    key=lambda path: path.stat().st_mtime if path.exists() else 0,
    reverse=True,
)

result = {
    "checked_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "login_log_found": False,
    "classification": "login_log_not_found",
    "log_size_bytes": None,
    "log_sha256": None,
    "safe_signals": [],
}

if candidates:
    path = candidates[0]
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace").lower()
    signals = []
    classification = "unknown_login_failure"

    pattern_groups = [
        (
            "device_code_not_enabled",
            [
                "device code login is not enabled",
                "device code authentication is not enabled",
                "device auth is not enabled",
                "device authorization is disabled",
            ],
        ),
        (
            "device_code_expired_or_cancelled",
            ["device code expired", "authorization expired", "access_denied", "authorization denied", "cancelled"],
        ),
        (
            "localhost_callback_issue",
            ["localhost:1455", "failed to bind", "address already in use", "callback server"],
        ),
        (
            "workspace_or_account_policy_blocked",
            ["workspace", "not allowed", "permission denied", "policy", "mfa required"],
        ),
        (
            "login_network_or_tls_failure",
            ["certificate", "tls", "dns", "connection refused", "connection reset", "network error"],
        ),
    ]

    for name, patterns in pattern_groups:
        matched = [pattern for pattern in patterns if pattern in text]
        if matched:
            classification = name
            signals.extend(matched)
            break

    result.update(
        {
            "login_log_found": True,
            "classification": classification,
            "log_size_bytes": len(raw),
            "log_sha256": hashlib.sha256(raw).hexdigest(),
            "safe_signals": signals,
        }
    )

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

commit_logs() {
  cd "$ORIS_DIR" || return 1
  local files=("$RUN_LOG")
  [ -f "$ADMIN_LOG" ] && files+=("$ADMIN_LOG")
  [ -f "$SYSTEMD_LOG" ] && files+=("$SYSTEMD_LOG")
  [ -f "$LOGIN_DIAGNOSTIC" ] && files+=("$LOGIN_DIAGNOSTIC")
  git add -- "${files[@]}" 2>/dev/null || true
  if git diff --cached --quiet -- "${files[@]}"; then
    LOG_COMMIT="NO_LOG_CHANGES"
    return 0
  fi
  git commit --only -m "test(dev-employee): record Codex device login verification $STAMP" -- "${files[@]}" > "$TMP_OUTPUT" 2>&1
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
  echo "CODE_HARDENING_COMMIT=$HARDENING_COMMIT"
  echo "DEVICE_AUTH_LOGIN=$DEVICE_AUTH_LOGIN"
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

if [ ! -t 0 ] || [ ! -t 1 ]; then
  FAILURE_CODE="interactive_tty_required"
  NEXT_ACTION="RUN_FROM_INTERACTIVE_ADMIN_SSH_SESSION"
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
  echo "===== code state ====="
  echo "head=$(git rev-parse HEAD 2>/dev/null || true)"
  echo "hardening_commit=$HARDENING_COMMIT"
} > "$RUN_LOG" 2>&1

systemctl --user stop "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1
if [ "$(systemctl --user is-active "$BRIDGE_SERVICE" 2>/dev/null || true)" = "active" ]; then
  FAILURE_CODE="bridge_stop_failed"
  fail_and_finish "INSPECT_BRIDGE_SERVICE"
fi
log_line "bridge_stopped=true"

if ! git merge-base --is-ancestor "$HARDENING_COMMIT" HEAD 2>/dev/null; then
  FAILURE_CODE="hardening_commit_not_present"
  fail_and_finish "PULL_MAIN_AND_RERUN"
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

cat <<'NOTICE'

在继续前，请在浏览器中的 ChatGPT 完成以下设置：
Settings → Security → 启用 Device code login。

完成后回到此终端按 Enter。接下来终端会显示登录网址和一次性代码；
请在你自己的浏览器中完成登录。不要把网址、代码或任何 Token 发到聊天或 GitHub。
NOTICE
read -r -p "Device code login 已启用，按 Enter 继续：" _CONFIRM

"$CODEX_BIN" logout >/dev/null 2>&1 || true
"$CODEX_BIN" login --device-auth
LOGIN_RC="$?"

if [ "$LOGIN_RC" -ne 0 ]; then
  DEVICE_AUTH_LOGIN="FAILED"
  write_login_diagnostic
  FAILURE_CODE="$(json_field "$LOGIN_DIAGNOSTIC" classification)"
  [ -z "$FAILURE_CODE" ] && FAILURE_CODE="device_auth_login_failed"
  fail_and_finish "INSPECT_SANITIZED_LOGIN_DIAGNOSTIC"
fi
DEVICE_AUTH_LOGIN="PASS"
log_line "device_auth_login=PASS"

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
  fail_and_finish "INSPECT_ADMIN_CODEX_PREFLIGHT"
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
