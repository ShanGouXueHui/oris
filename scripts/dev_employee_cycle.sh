#!/usr/bin/env bash

# ORIS Dev Employee single-command cycle runner.
# Purpose: pull latest code, run validation/smoke, write decision-useful logs,
# commit/push logs, and print a compact KEY_RESULT for the next iteration.

ROOT_DIR="${ORIS_REPO_DIR:-$HOME/projects/oris}"
BRANCH="${ORIS_BRANCH:-main}"
TASK_CODE="${ORIS_TASK_CODE:-dev_employee_cycle}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DAY="$(date -u +%Y%m%d)"
LOG_DIR="logs/dev_employee/${DAY}"
RUN_DIR="run/dev_employee/cycle/${TS}"
SUMMARY_FILE="${LOG_DIR}/${TASK_CODE}_${TS}.summary.md"
VALIDATION_FILE="${LOG_DIR}/${TASK_CODE}_${TS}.validation.txt"
KEY_RESULT_FILE="${RUN_DIR}/key_result.json"

mkdir -p "$ROOT_DIR"
cd "$ROOT_DIR" || exit 1

mkdir -p "$LOG_DIR" "$RUN_DIR"

{
  echo "# Dev Employee Cycle Summary"
  echo
  echo "- timestamp_utc: ${TS}"
  echo "- branch: ${BRANCH}"
  echo "- repo_dir: ${ROOT_DIR}"
  echo "- task_code: ${TASK_CODE}"
  echo
  echo "## Git pull"
} > "$SUMMARY_FILE"

{
  echo "===== ORIS DEV EMPLOYEE CYCLE ${TS} ====="
  echo "ROOT_DIR=${ROOT_DIR}"
  echo "BRANCH=${BRANCH}"
  echo "TASK_CODE=${TASK_CODE}"
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
from oris_vnext.validation import ValidationPipeline, load_runtime_config, write_validation_report
cfg = load_runtime_config("config/dev_employee_runtime.json")
report = ValidationPipeline(cfg).run()
out = Path("run/dev_employee/cycle_validation_report.json")
write_validation_report(out, report)
print(json.dumps({"ok": report.ok, "check_count": len(report.checks), "report_path": str(out)}, ensure_ascii=False, sort_keys=True))
raise SystemExit(0 if report.ok else 1)
PY
VALIDATION_RC=$?
VALIDATION_JSON="$(tail -n 1 run/dev_employee/cycle_validation_stdout.json 2>/dev/null || true)"
cat run/dev_employee/cycle_validation_stdout.json >> "$VALIDATION_FILE" 2>/dev/null || true

echo "- validation_rc: ${VALIDATION_RC}" >> "$SUMMARY_FILE"
echo "- validation_json: ${VALIDATION_JSON}" >> "$SUMMARY_FILE"

OK=false
if [ "$PULL_RC" -eq 0 ] && [ "$PULL2_RC" -eq 0 ] && [ "$COMPILE_RC" -eq 0 ] && [ "$SMOKE_RC" -eq 0 ] && [ "$VALIDATION_RC" -eq 0 ]; then
  OK=true
fi

{
  echo
  echo "## Key result"
  echo
  echo "\`\`\`json"
  printf '{"ok":%s,"timestamp_utc":"%s","compile_rc":%s,"smoke_rc":%s,"validation_rc":%s,"summary_file":"%s","validation_file":"%s"}\n' "$OK" "$TS" "$COMPILE_RC" "$SMOKE_RC" "$VALIDATION_RC" "$SUMMARY_FILE" "$VALIDATION_FILE"
  echo "\`\`\`"
  echo
  echo "## Last ledger lines"
  echo
  echo "\`\`\`jsonl"
  tail -n 5 run/dev_employee/task_runs.jsonl 2>/dev/null || true
  echo "\`\`\`"
} >> "$SUMMARY_FILE"

printf '{"ok":%s,"timestamp_utc":"%s","compile_rc":%s,"smoke_rc":%s,"validation_rc":%s,"summary_file":"%s","validation_file":"%s"}\n' "$OK" "$TS" "$COMPILE_RC" "$SMOKE_RC" "$VALIDATION_RC" "$SUMMARY_FILE" "$VALIDATION_FILE" > "$KEY_RESULT_FILE"

{
  echo
  echo "===== git diff summary before log commit ====="
  git status --short
} >> "$VALIDATION_FILE"

git add "$SUMMARY_FILE" "$VALIDATION_FILE" .gitignore scripts/dev_employee_cycle.sh 2>> "$VALIDATION_FILE"
if git diff --cached --quiet; then
  COMMIT_RC=0
  PUSH_RC=0
  echo "- log_commit: no_changes" >> "$SUMMARY_FILE"
else
  git commit -m "logs(dev-employee): record cycle ${TS}" >> "$VALIDATION_FILE" 2>&1
  COMMIT_RC=$?
  if [ "$COMMIT_RC" -eq 0 ]; then
    git push origin "$BRANCH" >> "$VALIDATION_FILE" 2>&1
    PUSH_RC=$?
  else
    PUSH_RC=99
  fi
  echo "- log_commit_rc: ${COMMIT_RC}" >> "$SUMMARY_FILE"
  echo "- log_push_rc: ${PUSH_RC}" >> "$SUMMARY_FILE"
fi

KEY_RESULT="$(cat "$KEY_RESULT_FILE")"
echo "KEY_RESULT=${KEY_RESULT}"
echo "SUMMARY_FILE=${SUMMARY_FILE}"
echo "VALIDATION_FILE=${VALIDATION_FILE}"
echo "LAST_LEDGER="
tail -n 3 run/dev_employee/task_runs.jsonl 2>/dev/null || true

if [ "$OK" = "true" ]; then
  exit 0
fi
exit 1
