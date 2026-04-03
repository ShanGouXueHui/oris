# PROJECT STATE

## As of 2026-04-03
The server was reset and rebuilt from scratch, and the OpenClaw baseline has now been successfully restored.

## Current baseline
- Execution user: `admin`
- Project repo path: `~/projects/oris`
- Python helper venv: `~/venvs/oris`
- OpenClaw CLI path is available through `~/.npm-global/bin/openclaw`
- OpenClaw runtime config: `~/.openclaw/openclaw.json`
- OpenClaw workspace: `~/.openclaw/workspace`

## Installed and verified
- OpenClaw onboarding completed successfully
- Gateway service installed as systemd user service
- Service name: `openclaw-gateway.service`
- Gateway bind: `127.0.0.1`
- Gateway port: `18789`
- Gateway status: running
- RPC probe: ok
- Default model: `openrouter/auto`
- OpenRouter auth is configured and effective

## Security state
- `gateway.controlUi.allowInsecureAuth` has been changed from `true` to `false`
- Gateway remains loopback-only
- `loginctl enable-linger admin` was enabled during onboarding
- Remaining audit warnings are currently non-blocking:
  1. `gateway.trusted_proxies_missing` because no reverse proxy is configured
  2. `gateway.nodes.deny_commands_ineffective` because some deny list command names are not exact matches

## Web search state
- DuckDuckGo provider was selected during onboarding
- Web search is not active yet because the provider still expects key/config completion in the current runtime

## Continuity notes
Future sessions should read:
1. `README.md`
2. `docs/PROJECT_STATE.md`
3. `memory/HANDOFF.md`
4. latest file under `docs/DECISIONS/`

## Next recommended steps
1. Decide how Control UI should be accessed:
   - local only via SSH tunnel
   - or later via reverse proxy / Tailscale
2. Decide whether to configure a real web search provider
3. Decide whether to connect a first channel such as Feishu/Lark
