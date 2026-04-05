# HANDOFF

## What is already working
- OpenClaw baseline is installed and stable under `admin`
- Public dashboard works at `https://control.orisfy.com`
- Nginx + HTTPS + Basic Auth are working
- OpenClaw gateway is still loopback-only on `127.0.0.1:18789`
- Gateway token is SecretRef-managed
- OpenRouter model auth is working again
- Feishu websocket channel is working
- Feishu bot pairing was completed successfully
- Feishu bot already replied successfully in DM

## Important paths
- Repo: `~/projects/oris`
- OpenClaw config: `~/.openclaw/openclaw.json`
- OpenClaw workspace: `~/.openclaw/workspace`
- Secrets file: `~/.openclaw/secrets.json`
- Auth profiles: `~/.openclaw/agents/main/agent/auth-profiles.json`

## Security posture
- Keep OpenClaw loopback-only
- Keep public access at the reverse-proxy layer only
- Do not commit secrets into GitHub
- Rotate Feishu App Secret before final production hardening

## Next recommended steps
1. Decide whether to add QQ Bot / Tencent-side channel
2. Rotate Feishu App Secret and update `~/.openclaw/secrets.json`
3. Re-verify Feishu after secret rotation
4. Optionally refine Feishu allowlist / group policy / operator workflow
