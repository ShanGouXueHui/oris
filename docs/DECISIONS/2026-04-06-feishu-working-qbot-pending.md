# Decision: proceed with Feishu now, defer QQ Bot until platform approval completes
Date: 2026-04-06

## Context
ORIS needed at least one working production-like channel. Feishu was fully configured and validated first. QQ Bot approval is still pending on the platform side.

## Decisions
1. Use Feishu as the first confirmed working external chat channel.
2. Keep Feishu in websocket mode.
3. Keep DM access control at `pairing` during baseline phase.
4. Defer QQ Bot implementation until platform approval completes.
5. Treat QQ Bot (`q.qq.com`) and WeChat dialogue platform (`chatbot.weixin.qq.com`) as separate products and separate integration paths.
6. Continue using unified secret storage via `~/.openclaw/secrets.json`.

## Outcome
- Feishu channel is already working end-to-end.
- QQ Bot work is paused only because of external approval lead time, not because of unresolved runtime architecture.

## Follow-up
- Resume QQ Bot once platform approval completes and `AppID` + `AppSecret` are available.
- Rotate Feishu App Secret before final hardening because it was exposed during setup.
