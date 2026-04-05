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

## Provider orchestration latest status (2026-04-06)
- OpenRouter catalog auto-refresh is working and currently discovers hundreds of models dynamically.
- Active routing automation is working and writes `orchestration/active_routing.json`.
- Gemini direct probe is healthy and Gemini models are now part of the automatic routing pool.
- Current routing outcomes include:
  - `free_fallback` -> Gemini Flash Lite path
  - `cn_candidate_pool` -> Gemini Flash path
- Zhipu direct probe is no longer blocked by wrong model naming; the current blocker is insufficient balance / missing resource package on the account side.
- Therefore ORIS is correctly falling back to Gemini instead of waiting for Zhipu.

## Active routing latest state (2026-04-06)
Current routing decisions after Bailian/Hunyuan integration:
- `primary_general` -> `openrouter/auto`
- `free_fallback` -> `qwen3.6-plus`
- `coding` -> `qwen-coder-turbo-0919`
- `cn_candidate_pool` -> `qwen3.6-plus`

Interpretation:
- Bailian is now active in real routing, not just in probe results
- Hunyuan is healthy and in the pool
- Gemini remains healthy and available as a fallback candidate

