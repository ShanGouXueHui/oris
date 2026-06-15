#!/usr/bin/env bash

cd /home/admin/projects/oris || exit 1
exec bash scripts/dev_employee_deploy_queue_lifecycle_hardening_v2_20260616.sh "$@"
