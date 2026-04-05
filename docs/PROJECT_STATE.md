# PROJECT STATE

## As of 2026-04-06
ORIS baseline is operational end-to-end on the rebuilt server.

## Runtime baseline
- Execution user: `admin`
- Repo path: `~/projects/oris`
- Python helper venv: `~/venvs/oris`
- OpenClaw config: `~/.openclaw/openclaw.json`
- OpenClaw workspace: `~/.openclaw/workspace`
- OpenClaw secrets file: `~/.openclaw/secrets.json`
- Gateway service: `openclaw-gateway.service` (systemd user service)
- Gateway bind: `127.0.0.1`
- Gateway port: `18789`

## Control plane status
- Public dashboard domain: `https://control.orisfy.com`
- Public access topology:
  - Nginx reverse proxy
  - HTTPS via Certbot / Let's Encrypt
  - Basic Auth in front of OpenClaw
  - OpenClaw gateway remains loopback-only
- `gateway.trustedProxies` and `gateway.controlUi.allowedOrigins` were configured for reverse-proxy access.
- `gateway.controlUi.allowInsecureAuth` was disabled.
- `gateway.auth.token` is SecretRef-managed, so dashboard URLs no longer embed token values.

## Model and secret management
- OpenRouter model auth is working.
- OpenRouter auth is configured via:
  - `~/.openclaw/agents/main/agent/auth-profiles.json`
  - `keyRef`
  - `~/.openclaw/secrets.json`
- `openclaw models status --probe` succeeded.
- `openclaw secrets audit --check` is clean.
- Real passwords, tokens, and secrets must not be committed into GitHub.

## Feishu channel status
- Feishu channel is enabled.
- Connection mode: `websocket`
- Account: `main`
- DM policy: `pairing`
- Group policy: `allowlist`
- Feishu app configuration and publish flow were completed.
- Event subscription mode is long connection.
- Event `im.message.receive_v1` is enabled.
- Private-message test succeeded.
- Pairing succeeded for at least one Feishu sender.
- Bot replied successfully (`pong`), confirming end-to-end Feishu channel health.

## QQ Bot / Tencent-side status
- QQ Bot integration has not been implemented yet.
- Current blocker: platform approval is still pending and may take several working days.
- Important distinction:
  - `q.qq.com` is the correct QQ Bot / QQ Open Platform route for OpenClaw `qqbot`
  - `chatbot.weixin.qq.com` is WeChat dialogue platform and is not the same integration target
- When QQ Bot approval completes, retrieve `AppID` and `AppSecret` from the QQ Bot platform and continue integration from there.

## Deferred hardening
- The Feishu App Secret was exposed during setup and must be rotated before final production hardening.
- Do not write real credentials into repository files.

## Continuity rules
Future sessions should read in this order:
1. `README.md`
2. `docs/PROJECT_STATE.md`
3. `memory/HANDOFF.md`
4. latest file under `docs/DECISIONS/`
