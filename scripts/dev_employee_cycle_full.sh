#!/usr/bin/env bash

ROOT_DIR="${ORIS_REPO_DIR:-$HOME/projects/oris}"
BRANCH="${ORIS_BRANCH:-main}"
cd "$ROOT_DIR" || exit 1

bash scripts/dev_employee_cycle.sh
CYCLE_RC=$?

python3 scripts/dev_employee_export_task_list.py
TASK_LIST_RC=$?

python3 scripts/dev_employee_export_task_status.py
TASK_STATUS_RC=$?

python3 scripts/dev_employee_export_task_binding.py
BINDING_RC=$?

python3 scripts/dev_employee_export_plan_audit.py
PLAN_AUDIT_RC=$?

python3 scripts/dev_employee_export_commercial_readiness.py
READINESS_RC=$?

git add \
  logs/dev_employee/latest_task_list.json \
  logs/dev_employee/latest_task_list.md \
  logs/dev_employee/latest_task_status.json \
  logs/dev_employee/latest_task_status.md \
  logs/dev_employee/latest_task_binding.json \
  logs/dev_employee/latest_task_binding.md \
  logs/dev_employee/latest_plan_audit.json \
  logs/dev_employee/latest_plan_audit.md \
  logs/dev_employee/latest_commercial_readiness.json \
  logs/dev_employee/latest_commercial_readiness.md \
  scripts/dev_employee_cycle_full.sh \
  scripts/dev_employee_export_task_list.py \
  scripts/dev_employee_export_task_status.py \
  scripts/dev_employee_export_task_binding.py \
  scripts/dev_employee_export_plan_audit.py \
  scripts/dev_employee_export_commercial_readiness.py \
  oris_vnext/task_binding.py \
  oris_vnext/plan_audit.py \
  oris_vnext/commercial_readiness.py \
  config/dev_employee_task_status.json \
  config/dev_employee_commercial_readiness.json 2>/dev/null || true

COMMIT_RC=0
PUSH_RC=0
if ! git diff --cached --quiet; then
  git commit -m "logs(dev-employee): update full-cycle artifacts" >/tmp/oris_dev_employee_cycle_full_git.log 2>&1
  COMMIT_RC=$?
  if [ "$COMMIT_RC" -eq 0 ]; then
    git push origin "$BRANCH" >>/tmp/oris_dev_employee_cycle_full_git.log 2>&1
    PUSH_RC=$?
  else
    PUSH_RC=99
  fi
fi

HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "FULL_CYCLE_REF=${HEAD_SHORT} logs/dev_employee/latest_task_list.json logs/dev_employee/latest_task_status.json logs/dev_employee/latest_task_binding.json logs/dev_employee/latest_plan_audit.json logs/dev_employee/latest_commercial_readiness.json"
echo "FULL_CYCLE_RESULT={\"cycle_rc\":${CYCLE_RC},\"task_list_rc\":${TASK_LIST_RC},\"task_status_rc\":${TASK_STATUS_RC},\"binding_rc\":${BINDING_RC},\"plan_audit_rc\":${PLAN_AUDIT_RC},\"readiness_rc\":${READINESS_RC},\"commit_rc\":${COMMIT_RC},\"push_rc\":${PUSH_RC}}"

if [ "$CYCLE_RC" -eq 0 ] && [ "$TASK_LIST_RC" -eq 0 ] && [ "$TASK_STATUS_RC" -eq 0 ] && [ "$BINDING_RC" -eq 0 ] && [ "$PLAN_AUDIT_RC" -eq 0 ] && [ "$READINESS_RC" -eq 0 ] && [ "$COMMIT_RC" -eq 0 ] && [ "$PUSH_RC" -eq 0 ]; then
  exit 0
fi
exit 1
