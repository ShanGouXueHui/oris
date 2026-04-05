# HANDOFF

## What is already working
- OpenClaw baseline is installed and stable under `admin`
- Public dashboard works at `https://control.orisfy.com`
- Nginx + HTTPS + Basic Auth are working
- OpenClaw gateway is loopback-only on `127.0.0.1:18789`
- Gateway token is SecretRef-managed
- OpenRouter model auth is working
- Feishu websocket channel is working
- Feishu bot pairing was completed successfully
- Feishu bot already replied successfully in DM (`pong`)

## Important paths
- Repo: `~/projects/oris`
- OpenClaw config: `~/.openclaw/openclaw.json`
- OpenClaw workspace: `~/.openclaw/workspace`
- Secrets file: `~/.openclaw/secrets.json`
- Auth profiles: `~/.openclaw/agents/main/agent/auth-profiles.json`

## Operational rules
- Keep OpenClaw loopback-only
- Keep public access at the reverse-proxy layer only
- Do not commit secrets into GitHub
- Use copy-paste executable commands only
- Do not use `set -e`
- Validate each step before commit/push

## Feishu notes
- Feishu uses websocket mode, not webhook mode
- Event subscription mode in Feishu developer console is long connection
- Event `im.message.receive_v1` is enabled
- Current DM access control is `pairing`
- The exposed Feishu App Secret still needs rotation before final hardening

## QQ Bot notes
- QQ Bot is not yet connected
- Approval is pending on the QQ platform and may take several working days
- The WeChat dialogue platform (`chatbot.weixin.qq.com`) is not the same thing as QQ Bot for OpenClaw
- Resume QQ Bot integration only after approval completes and correct `AppID` + `AppSecret` are available from QQ Bot platform

## Recommended next steps
1. Continue non-channel work while QQ Bot approval is pending
2. After QQ Bot approval, retrieve `AppID` and `AppSecret`
3. Integrate QQ Bot using the same `~/.openclaw/secrets.json` architecture
4. Rotate Feishu App Secret before final production hardening
