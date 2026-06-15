#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1
exec bash scripts/dev_employee_resume_codex_auth_hardening_20260616.sh "$@"
