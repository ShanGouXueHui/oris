# PROJECT STATE

## As of 2026-04-06
ORIS baseline is now working end-to-end on the rebuilt server.

## Current runtime baseline
- Execution user: `admin`
- Repo path: `~/projects/oris`
- Python helper venv: `~/venvs/oris`
- OpenClaw runtime config: `~/.openclaw/openclaw.json`
- OpenClaw workspace: `~/.openclaw/workspace`
- Gateway service: `openclaw-gateway.service` (systemd user service)
- Gateway bind: `127.0.0.1`
- Gateway port: `18789`

## Control plane
- Public dashboard domain: `https://control.orisfy.com`
- Public access path is implemented as:
  - Nginx reverse proxy
  - HTTPS via Certbot / Let's Encrypt
  - Basic Auth in front of OpenClaw
  - OpenClaw gateway remains loopback-only
- `gateway.trustedProxies` and `gateway.controlUi.allowedOrigins` were configured for the reverse-proxy topology.
- `gateway.controlUi.allowInsecureAuth` has been disabled.

## Secrets and auth
- `gateway.auth.token` is now SecretRef-managed.
- `openclaw dashboard --no-open` now outputs a clean dashboard URL without embedding the token.
- OpenRouter auth is restored and working through:
  - `auth-profiles.json`
  - `keyRef`
  - `~/.openclaw/secrets.json`
- `openclaw models status --probe` is successful.
- `openclaw secrets audit --check` is clean.

## Feishu channel
- Feishu channel is enabled.
- Connection mode: `websocket`
- Account: `main`
- DM policy: `pairing`
- Group policy: `allowlist`
- Feishu app was configured and published.
- Event subscription mode is set to long connection.
- Event `im.message.receive_v1` is enabled.
- Private-message test succeeded.
- Pairing succeeded for at least one Feishu sender.
- Bot replied successfully (`pong`), confirming the full channel path is working.

## Continuity rules
Future sessions should read in this order:
1. `README.md`
2. `docs/PROJECT_STATE.md`
3. `memory/HANDOFF.md`
4. latest file under `docs/DECISIONS/`

## Deferred hardening
The Feishu App Secret was exposed during setup and must be rotated before final production hardening.
Do not store any real passwords, tokens, or secrets in this repository.
