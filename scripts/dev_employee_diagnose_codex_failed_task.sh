#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1

TASK_ID="${1:-}"
if [ -z "$TASK_ID" ]; then
  read -p "Failed task ID: " TASK_ID
fi
if [ -z "$TASK_ID" ]; then
  echo "TASK_ID_REQUIRED"
  exit 1
fi

ENV_FILE="$HOME/.config/oris/dev_employee_enqueue.env"
LOG_DIR="logs/dev_employee/codex_failed_diagnostics"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_FILE="$LOG_DIR/${TASK_ID}-${STAMP}.log"
STATUS_FILE="/tmp/oris-codex-failed-status-$$.json"
MATCH_FILE="/tmp/oris-codex-failed-matches-$$.txt"
mkdir -p "$LOG_DIR"

sanitize_stream() {
  python3 -c '
import re, sys
text = sys.stdin.read()
patterns = [
    (r"(?i)(ORIS_DEV_EMPLOYEE_(?:WEB_CONSOLE|INTAKE)_TOKEN=)[^\\s\\\"\\x27]+", r"\\1<REDACTED>"),
    (r"(?i)(x-oris-(?:console-)?token[\\\"\\x27:]*(?:\\s*=|\\s*:)?\\s*)[^\\s,}\\\"\\x27]+", r"\\1<REDACTED>"),
    (r"(?i)(authorization[\\\"\\x27:]*(?:\\s*=|\\s*:)?\\s*)[^\\n,}]+", r"\\1<REDACTED>"),
    (r"(?i)(api[_-]?key[\\\"\\x27:]*(?:\\s*=|\\s*:)?\\s*)[^\\s,}\\\"\\x27]+", r"\\1<REDACTED>"),
]
for pattern, repl in patterns:
    text = re.sub(pattern, repl, text)
sys.stdout.write(text)
'
}

collect_file() {
  local file="$1"
  echo "----- FILE: $file -----"
  if [ -r "$file" ]; then
    tail -n 240 "$file" 2>&1 | sanitize_stream
  else
    sudo tail -n 240 "$file" 2>&1 | sanitize_stream || true
  fi
  echo
}

FINAL_STATUS="unknown"
LIKELY_CAUSE="not_yet_classified"
MATCH_COUNT="0"

{
  echo "===== timestamp ====="
  date -Is
  echo
  echo "===== task ====="
  echo "TASK_ID=$TASK_ID"
  echo

  echo "===== git state ====="
  git rev-parse HEAD || true
  git status --short || true
  echo

  echo "===== local Web Console task status ====="
  TOKEN=""
  if [ -f "$ENV_FILE" ]; then
    TOKEN="$(awk -F= '/^ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN=/ {print substr($0, index($0, "=")+1)}' "$ENV_FILE" | tail -n 1)"
  fi
  if [ -n "$TOKEN" ]; then
    HTTP_CODE="$(curl -sS -o "$STATUS_FILE" -w '%{http_code}' -H "X-ORIS-Console-Token: $TOKEN" "http://127.0.0.1:18893/api/goals/$TASK_ID" || true)"
    echo "WEB_STATUS_HTTP=$HTTP_CODE"
    python3 -m json.tool "$STATUS_FILE" 2>/dev/null | sanitize_stream || cat "$STATUS_FILE" | sanitize_stream || true
    FINAL_STATUS="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data=json.load(open(sys.argv[1], encoding='utf-8'))
    print(data.get('status') or 'unknown')
except Exception:
    print('unknown')
PY
)"
  else
    echo "CONSOLE_TOKEN_MISSING"
  fi
  echo

  echo "===== status service task payload ====="
  python3 scripts/dev_employee_task_status.py --task-id "$TASK_ID" 2>&1 | sanitize_stream || true
  echo

  echo "===== matching task files ====="
  : > "$MATCH_FILE"
  for root in orchestration run logs memory; do
    if [ -d "$root" ]; then
      find "$root" -type f -size -2097152c -print0 2>/dev/null \
        | xargs -0 grep -Il -- "$TASK_ID" 2>/dev/null >> "$MATCH_FILE" || true
      find "$root" -type f -name "*${TASK_ID}*" -size -2097152c 2>/dev/null >> "$MATCH_FILE" || true
    fi
  done
  sort -u "$MATCH_FILE" -o "$MATCH_FILE"
  MATCH_COUNT="$(wc -l < "$MATCH_FILE" | tr -d ' ')"
  echo "MATCH_COUNT=$MATCH_COUNT"
  sed -n '1,120p' "$MATCH_FILE"
  echo

  echo "===== matching task file excerpts ====="
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    collect_file "$file"
  done < <(sed -n '1,30p' "$MATCH_FILE")
  echo

  echo "===== bridge service status ====="
  systemctl --user status oris-dev-employee-bridge.service --no-pager -l 2>&1 | sanitize_stream || true
  echo

  echo "===== bridge journal tail ====="
  journalctl --user -u oris-dev-employee-bridge.service --since '2026-06-16 03:00:00' --no-pager -o short-iso 2>&1 \
    | tail -n 320 | sanitize_stream || true
  echo

  echo "===== intake and Web Console journal tail ====="
  journalctl --user -u oris-dev-employee-intake.service -u oris-dev-employee-web-console.service \
    --since '2026-06-16 03:00:00' --no-pager -o short-iso 2>&1 | tail -n 200 | sanitize_stream || true
  echo

  echo "===== Codex executable ====="
  command -v codex || true
  codex --version 2>&1 | sanitize_stream || true
  if [ -x /home/admin/.npm-global/lib/node_modules/@openai/codex/bin/codex.js ]; then
    node /home/admin/.npm-global/lib/node_modules/@openai/codex/bin/codex.js --version 2>&1 | sanitize_stream || true
  fi
  echo

  echo "===== product repository ====="
  if [ -d /home/admin/projects/oris-final-acceptance-api/.git ]; then
    git -C /home/admin/projects/oris-final-acceptance-api status --short || true
    git -C /home/admin/projects/oris-final-acceptance-api log -5 --oneline || true
    git -C /home/admin/projects/oris-final-acceptance-api remote -v || true
    echo "LOCAL_HEAD=$(git -C /home/admin/projects/oris-final-acceptance-api rev-parse HEAD 2>/dev/null || true)"
    echo "REMOTE_HEAD=$(git -C /home/admin/projects/oris-final-acceptance-api ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}')"
  else
    echo "PRODUCT_REPO_MISSING"
  fi
  echo

  echo "===== classify likely cause ====="
  CLASSIFY_SOURCE="$(cat "$STATUS_FILE" 2>/dev/null; while IFS= read -r file; do [ -r "$file" ] && tail -n 240 "$file"; done < "$MATCH_FILE"; journalctl --user -u oris-dev-employee-bridge.service --since '2026-06-16 03:00:00' --no-pager 2>/dev/null | tail -n 320)"
  if printf '%s' "$CLASSIFY_SOURCE" | grep -Eqi '401|unauthorized|authentication|login required|not logged in'; then
    LIKELY_CAUSE="codex_authentication"
  elif printf '%s' "$CLASSIFY_SOURCE" | grep -Eqi '402|billing|insufficient.*credit|quota'; then
    LIKELY_CAUSE="provider_billing_or_quota"
  elif printf '%s' "$CLASSIFY_SOURCE" | grep -Eqi '429|rate.?limit|too many requests'; then
    LIKELY_CAUSE="rate_limit"
  elif printf '%s' "$CLASSIFY_SOURCE" | grep -Eqi 'permission denied|operation not permitted|read-only file system'; then
    LIKELY_CAUSE="filesystem_permission"
  elif printf '%s' "$CLASSIFY_SOURCE" | grep -Eqi 'timed out|timeout|deadline exceeded'; then
    LIKELY_CAUSE="timeout"
  elif printf '%s' "$CLASSIFY_SOURCE" | grep -Eqi 'network|connection refused|could not resolve|temporary failure|TLS|certificate'; then
    LIKELY_CAUSE="network_or_tls"
  elif printf '%s' "$CLASSIFY_SOURCE" | grep -Eqi 'not a git repository|repository.*not found|remote.*not found'; then
    LIKELY_CAUSE="repository_configuration"
  elif printf '%s' "$CLASSIFY_SOURCE" | grep -Eqi 'codex.*failed|exit[_ ]?code|return[_ ]?code'; then
    LIKELY_CAUSE="codex_nonzero_exit_unclassified"
  else
    LIKELY_CAUSE="not_yet_classified"
  fi
  echo "FINAL_STATUS=$FINAL_STATUS"
  echo "LIKELY_CAUSE=$LIKELY_CAUSE"
  echo
} > >(tee "$LOG_FILE") 2>&1
wait

rm -f "$STATUS_FILE" "$MATCH_FILE"

git add "$LOG_FILE"
if git diff --cached --quiet; then
  LOG_COMMIT="NO_CHANGES"
else
  git commit -m "test(dev-employee): diagnose codex failed task $TASK_ID"
  git push origin main
  LOG_COMMIT="$(git rev-parse --short HEAD)"
fi

BRIDGE_STATUS="$(systemctl --user is-active oris-dev-employee-bridge.service 2>/dev/null || true)"

echo
echo "===== SUMMARY ====="
echo "RESULT=DIAGNOSED"
echo "TASK_ID=$TASK_ID"
echo "FINAL_STATUS=$FINAL_STATUS"
echo "LIKELY_CAUSE=$LIKELY_CAUSE"
echo "MATCHED_LOCAL_FILES=$MATCH_COUNT"
echo "BRIDGE_SERVICE=$BRIDGE_STATUS"
echo "LOG_COMMIT=$LOG_COMMIT"
echo "NEXT_ACTION=send_this_summary_only_then_wait_for_root_cause_review"
echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
echo "===== END SUMMARY ====="
