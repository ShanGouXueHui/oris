# HANDOFF

## Machine status
- Fresh rebuilt Ubuntu server
- Execution user: `admin`
- Repo path: `~/projects/oris`
- Python helper venv: `~/venvs/oris`
- GitHub SSH key path: `~/.ssh/github_oris_ed25519`

## OpenClaw status
- Installed successfully under the `admin` user environment
- Onboarding completed successfully
- Gateway service is running under systemd user service
- Bind address: `127.0.0.1`
- Port: `18789`
- Default model: `openrouter/auto`
- OpenRouter key is effective
- Control UI insecure auth flag has been disabled

## Important path note
OpenClaw was installed under npm-global, so PATH must include:

`$HOME/.npm-global/bin`

Current fix was written into:
- `~/.bashrc`
- `~/.profile`

## Current non-blocking warnings
1. `gateway.trusted_proxies_missing`
2. `gateway.nodes.deny_commands_ineffective`

These do not block baseline usage in the current loopback-only single-user setup.

## Engineering rules
- Use copy-paste executable commands only
- Do not require manual file editing
- Do not use `set -e`
- Validate each step before commit/push
- Keep everything under the same execution user unless there is a very strong reason to isolate

## Immediate next action
Choose one of the following as the next workstream:
1. Configure Control UI access path
2. Configure web search provider
3. Configure first channel integration
