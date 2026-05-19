#!/usr/bin/env bash

ROOT_DIR="${ORIS_REPO_DIR:-$HOME/projects/oris}"
BRANCH="${ORIS_BRANCH:-main}"
SUMMARY="${ORIS_DEV_TASK_SUMMARY:-}"
OBJECTIVE="${ORIS_DEV_TASK_OBJECTIVE:-}"

cd "$ROOT_DIR" || exit 1

if [ -z "$SUMMARY" ] || [ -z "$OBJECTIVE" ]; then
  echo "ERROR: set ORIS_DEV_TASK_SUMMARY and ORIS_DEV_TASK_OBJECTIVE" >&2
  exit 2
fi

python3 scripts/dev_employee_export_task_intake.py
INTAKE_RC=$?

git add \
  logs/dev_employee/latest_task_intake.json \
  logs/dev_employee/latest_task_intake.md \
  scripts/dev_employee_submit_task.sh \
  scripts/dev_employee_export_task_intake.py \
  oris_vnext/task_intake.py \
  config/dev_employee_task_intake.json 2>/dev/null || true

COMMIT_RC=0
PUSH_RC=0
if ! git diff --cached --quiet; then
  git commit -m "logs(dev-employee): submit pilot task" >/tmp/oris_dev_employee_submit_task_git.log 2>&1
  COMMIT_RC=$?
  if [ "$COMMIT_RC" -eq 0 ]; then
    git push origin "$BRANCH" >>/tmp/oris_dev_employee_submit_task_git.log 2>&1
    PUSH_RC=$?
  else
    PUSH_RC=99
  fi
fi

bash scripts/dev_employee_cycle_full.sh
FULL_RC=$?

HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "TASK_SUBMIT_REF=${HEAD_SHORT} logs/dev_employee/latest_task_intake.json logs/dev_employee/latest_task_binding.json logs/dev_employee/latest_operator_dashboard.json"
echo "TASK_SUBMIT_RESULT={\"intake_rc\":${INTAKE_RC},\"commit_rc\":${COMMIT_RC},\"push_rc\":${PUSH_RC},\"full_rc\":${FULL_RC}}"

if [ "$INTAKE_RC" -eq 0 ] && [ "$COMMIT_RC" -eq 0 ] && [ "$PUSH_RC" -eq 0 ] && [ "$FULL_RC" -eq 0 ]; then
  exit 0
fi
exit 1
