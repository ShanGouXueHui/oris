#!/usr/bin/env bash

# ORIS Dev Employee single-command cycle runner.
# Purpose: pull latest code, run validation/smoke, write decision-useful logs,
# commit/push logs, and print only compact GitHub log references for iteration.

ROOT_DIR="${ORIS_REPO_DIR:-$HOME/projects/oris}"
BRANCH="${ORIS_BRANCH:-main}"
TASK_CODE="${ORIS_TASK_CODE:-dev_employee_cycle}"
SELF_HEAL_LOG_DRIFT="${ORIS_SELF_HEAL_LOG_DRIFT:-1}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DAY="$(date -u +%Y%m%d)"
LOG_DIR="logs/dev_employee/${DAY}"
RUN_DIR="run/dev_employee/cycle/${TS}"
SUMMARY_FILE="${LOG_DIR}/${TASK_CODE}_${TS}.summary.md"
VALIDATION_FILE="${LOG_DIR}/${TASK_CODE}_${TS}.validation.txt"
KEY_RESULT_FILE="${RUN_DIR}/key_result.json"
COMMIT_LOG_FILE="${RUN_DIR}/git_commit_push.log"
PREFLIGHT_STATUS_FILE="${RUN_DIR}/git_status_preflight.txt"
SELF_HEAL_FILE="${RUN_DIR}/self_heal_log_drift.txt"
VALIDATION_MD_FILE="${RUN_DIR}/validation_report.md"

mkdir -p "$ROOT_DIR"
cd "$ROOT_DIR" || exit 1

mkdir -p "$LOG_DIR" "$RUN_DIR"

git status --short > "$PREFLIGHT_STATUS_FILE" 2>/dev/null || true

# Previous buggy cycle versions appended to already-committed logs after commit.
# Restore only tracked Dev Employee log files before creating the new log pair.
# This is intentionally narrow and does not touch business/runtime dirty files.
if [ "$SELF_HEAL_LOG_DRIFT" = "1" ]; then
  awk '/^ M logs\/dev_employee\/.*\.(summary\.md|validation\.txt)$/ {print $2}' "$PREFLIGHT_STATUS_FILE" > "$SELF_HEAL_FILE" || true
  if [ -s "$SELF_HEAL_FILE" ]; then
    while IFS= read -r tracked_log_file; do
      git restore -- "$tracked_log_file" 2>/dev/null || true
    done < "$SELF_HEAL_FILE"
  fi
fi

{
  echo "# Dev Employee Cycle Summary"
  echo
  echo "- timestamp_utc: ${TS}"
  echo "- branch: ${BRANCH}"
  echo "- repo_dir: ${ROOT_DIR}"
  echo "- task_code: ${TASK_CODE}"
  echo "- self_heal_log_drift: ${SELF_HEAL_LOG_DRIFT}"
  echo
  echo "## Preflight status before self-heal"
  echo
  echo "\`\`\`text"
  cat "$PREFLIGHT_STATUS_FILE" || true
  echo "\`\`\`"
  echo
  echo "## Self-healed tracked dev_employee logs"
  echo
  echo "\`\`\`text"
  cat "$SELF_HEAL_FILE" 2>/dev/null || true
  echo "\`\`\`"
  echo
  echo "## Git pull"
} > "$SUMMARY_FILE"

{
  echo "===== ORIS DEV EMPLOYEE CYCLE ${TS} ====="
  echo "ROOT_DIR=${ROOT_DIR}"
  echo "BRANCH=${BRANCH}"
  echo "TASK_CODE=${TASK_CODE}"
  echo "SELF_HEAL_LOG_DRIFT=${SELF_HEAL_LOG_DRIFT}"
  echo
  echo "===== git status before self-heal ====="
  cat "$PREFLIGHT_STATUS_FILE" || true
  echo
  echo "===== self-healed tracked dev_employee logs ====="
  cat "$SELF_HEAL_FILE" 2>/dev/null || true
  echo
  echo "===== git status before pull ====="
  git status --short || true
  echo
  echo "===== git pull ====="
} > "$VALIDATION_FILE"

git checkout "$BRANCH" >> "$VALIDATION_FILE" 2>&1
PULL_RC=$?
git pull --ff-only origin "$BRANCH" >> "$VALIDATION_FILE" 2>&1
PULL2_RC=$?

echo "- git_checkout_rc: ${PULL_RC}" >> "$SUMMARY_FILE"
echo "- git_pull_rc: ${PULL2_RC}" >> "$SUMMARY_FILE"

COMPILE_RC=99
SMOKE_RC=99
VALIDATION_RC=99
SMOKE_JSON=""
VALIDATION_JSON=""

{
  echo
  echo "===== python compile ====="
} >> "$VALIDATION_FILE"
python3 -m compileall -q oris_vnext scripts/dev_employee_smoke.py >> "$VALIDATION_FILE" 2>&1
COMPILE_RC=$?
echo "- compile_rc: ${COMPILE_RC}" >> "$SUMMARY_FILE"

{
  echo
  echo "===== dev employee smoke ====="
} >> "$VALIDATION_FILE"
python3 scripts/dev_employee_smoke.py --dry-run --output-dir "$RUN_DIR/smoke" > "$RUN_DIR/smoke.stdout" 2> "$RUN_DIR/smoke.stderr"
SMOKE_RC=$?
cat "$RUN_DIR/smoke.stdout" >> "$VALIDATION_FILE"
cat "$RUN_DIR/smoke.stderr" >> "$VALIDATION_FILE"
SMOKE_JSON="$(tail -n 1 "$RUN_DIR/smoke.stdout" 2>/dev/null || true)"
echo "- smoke_rc: ${SMOKE_RC}" >> "$SUMMARY_FILE"
echo "- smoke_json: ${SMOKE_JSON}" >> "$SUMMARY_FILE"

{
  echo
  echo "===== validation pipeline ====="
} >> "$VALIDATION_FILE"
python3 - <<'PY' > "run/dev_employee/cycle_validation_stdout.json" 2>> "$VALIDATION_FILE"
import json
from pathlib import Path
from oris_vnext.validation import (
    ValidationPipeline,
    load_runtime_config,
    write_validation_markdown,
    write_validation_report,
)
cfg = load_runtime_config("config/dev_employee_runtime.json")
report = ValidationPipeline(cfg).run()
out = Path("run/dev_employee/cycle_validation_report.json")
md_out = Path("run/dev_employee/cycle_validation_report.md")
write_validation_report(out, report)
write_validation_markdown(md_out, report)
print(json.dumps({"ok": report.ok, "check_count": len(report.checks), "report_path": str(out), "markdown_path": str(md_out)}, ensure_ascii=False, sort_keys=True))
raise SystemExit(0 if report.ok else 1)
PY
VALIDATION_RC=$?
VALIDATION_JSON="$(tail -n 1 run/dev_employee/cycle_validation_stdout.json 2>/dev/null || true)"
cat run/dev_employee/cycle_validation_stdout.json >> "$VALIDATION_FILE" 2>/dev/null || true
echo "- validation_rc: ${VALIDATION_RC}" >> "$SUMMARY_FILE"
echo "- validation_json: ${VALIDATION_JSON}" >> "$SUMMARY_FILE"
cp run/dev_employee/cycle_validation_report.md "$VALIDATION_MD_FILE" 2>/dev/null || true

OK=false
if [ "$PULL_RC" -eq 0 ] && [ "$PULL2_RC" -eq 0 ] && [ "$COMPILE_RC" -eq 0 ] && [ "$SMOKE_RC" -eq 0 ] && [ "$VALIDATION_RC" -eq 0 ]; then
  OK=true
fi

{
  echo
  if [ -s "$VALIDATION_MD_FILE" ]; then
    cat "$VALIDATION_MD_FILE"
  fi
  echo
  echo "## Key result"
  echo
  echo "\`\`\`json"
  printf '{"ok":%s,"timestamp_utc":"%s","compile_rc":%s,"smoke_rc":%s,"validation_rc":%s,"summary_file":"%s","validation_file":"%s"}\n' "$OK" "$TS" "$COMPILE_RC" "$SMOKE_RC" "$VALIDATION_RC" "$SUMMARY_FILE" "$VALIDATION_FILE"
  echo "\`\`\`"
  echo
  echo "## Git status captured before log commit"
  echo
  echo "\`\`\`text"
  git status --short
  echo "\`\`\`"
} >> "$SUMMARY_FILE"

printf '{"ok":%s,"timestamp_utc":"%s","compile_rc":%s,"smoke_rc":%s,"validation_rc":%s,"summary_file":"%s","validation_file":"%s"}\n' "$OK" "$TS" "$COMPILE_RC" "$SMOKE_RC" "$VALIDATION_RC" "$SUMMARY_FILE" "$VALIDATION_FILE" > "$KEY_RESULT_FILE"

{
  echo
  echo "===== git diff summary before log commit ====="
  git status --short
} >> "$VALIDATION_FILE"

# Stage only decision-useful logs and known runner/config files. Do not stage runtime noise.
git add "$SUMMARY_FILE" "$VALIDATION_FILE" .gitignore scripts/dev_employee_cycle.sh config/dev_employee_runtime.json scripts/dev_employee_smoke.py oris_vnext/bootstrap_reader.py oris_vnext/validation.py 2>> "$COMMIT_LOG_FILE"
COMMIT_RC=0
PUSH_RC=0
if git diff --cached --quiet; then
  echo "no_changes" > "$COMMIT_LOG_FILE"
else
  git commit -m "logs(dev-employee): record cycle ${TS}" >> "$COMMIT_LOG_FILE" 2>&1
  COMMIT_RC=$?
  if [ "$COMMIT_RC" -eq 0 ]; then
    git push origin "$BRANCH" >> "$COMMIT_LOG_FILE" 2>&1
    PUSH_RC=$?
  else
    PUSH_RC=99
  fi
fi

HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
KEY_RESULT="$(cat "$KEY_RESULT_FILE")"

echo "GITHUB_LOG_REF=${HEAD_SHORT} ${SUMMARY_FILE} ${VALIDATION_FILE}"
echo "KEY_RESULT=${KEY_RESULT}"

if [ "$OK" = "true" ] && [ "$COMMIT_RC" -eq 0 ] && [ "$PUSH_RC" -eq 0 ]; then
  exit 0
fi
exit 1
