# Dev Employee Bridge Service Runbook

## Purpose

Run ORIS Dev Employee supervised bridge continuously as a user-level systemd service.

The service watches `orchestration/dev_employee_queue/*.queued.json`, claims tasks, invokes Codex CLI, performs host-side checks, pushes product commits, verifies GitHub remote state, and commits ORIS evidence.

## Service

- Unit: `oris-dev-employee-bridge.service`
- Unit source: `systemd/user/oris-dev-employee-bridge.service`
- Installed path: `~/.config/systemd/user/oris-dev-employee-bridge.service`
- Working directory: `/home/admin/projects/oris`
- Command: `/usr/bin/python3 /home/admin/projects/oris/scripts/dev_employee_supervised_bridge_v2.py --watch --interval 10`

## Install or update

```bash
cd /home/admin/projects/oris

git fetch origin main
git reset --hard origin/main

bash scripts/install_dev_employee_bridge_service.sh
```

## Status

```bash
systemctl --user status oris-dev-employee-bridge.service --no-pager
journalctl --user -u oris-dev-employee-bridge.service -n 120 --no-pager
```

## Stop

```bash
systemctl --user stop oris-dev-employee-bridge.service
```

## Restart

```bash
systemctl --user restart oris-dev-employee-bridge.service
```

## Recover stale tasks

```bash
cd /home/admin/projects/oris
python3 scripts/dev_employee_recover_stale_tasks.py --max-age-minutes 30 --fail-completed-running
```

## Evidence locations

- `logs/dev_employee/`
- `orchestration/task_runs/`
- `orchestration/dev_employee_queue/`

## Operating rule

Do not paste long logs into chat. Commit evidence to GitHub and inspect commit/file refs.
