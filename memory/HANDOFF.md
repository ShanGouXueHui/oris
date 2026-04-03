# HANDOFF

## Current machine state
- Fresh rebuilt Ubuntu server
- Execution user: `admin`
- Repo path: `~/projects/oris`
- Python helper venv: `~/venvs/oris`
- GitHub SSH key path: `~/.ssh/github_oris_ed25519`
- OpenClaw CLI has been installed
- OpenClaw onboarding is still pending

## Engineering rules
- Use copy-paste executable commands only
- Do not require manual file editing
- Do not use `set -e`
- Validate each step before commit/push
- Do not use cron to auto-commit or auto-push repository changes
- Persist stable conclusions to GitHub docs immediately after validation

## Read order for future sessions
1. `README.md`
2. `docs/PROJECT_STATE.md`
3. `memory/HANDOFF.md`
4. newest file under `docs/DECISIONS/`

## Immediate next action
Run OpenClaw onboarding and verify the gateway on the rebuilt server.
