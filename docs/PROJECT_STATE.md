# PROJECT STATE

## As of 2026-04-03
The server was reset and rebuilt from scratch.

## Current baseline
- Host baseline has been rebuilt.
- `admin` is the execution user.
- Python helper venv exists at: `~/venvs/oris`
- Project repo path: `~/projects/oris`
- OpenClaw is installed in the `admin` user environment.
- OpenClaw onboarding has not been completed yet on this rebuilt server.

## Runtime conventions
- OpenClaw runtime config path: `~/.openclaw/openclaw.json`
- OpenClaw runtime workspace path: `~/.openclaw/workspace`

## Project memory conventions
The GitHub repo acts as the project-side persistent memory layer.

Primary continuity files:
1. `README.md`
2. `docs/PROJECT_STATE.md`
3. `memory/HANDOFF.md`
4. `docs/DECISIONS/*.md`

## Next steps
1. Complete OpenClaw onboarding with the selected model provider and API key.
2. Verify:
   - `openclaw gateway status`
   - `openclaw dashboard`
   - `openclaw models status`
3. Continue ORIS system configuration and record every stable conclusion into repo docs.
