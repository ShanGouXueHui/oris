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
1. Build free token / free quota orchestration skeleton
2. Formalize Expert-01 (Insight Analyst) and Expert-02 (Coding Engineer)
3. Install only a minimal necessary skill set after readiness check
4. Resume QQ Bot only after platform approval completes
5. Rotate Feishu App Secret before final production hardening

## Provider orchestration latest status
- OpenRouter catalog refresh is automated
- Active routing selection is automated
- Gemini direct probe is healthy
- Gemini is now being selected automatically for fallback / candidate routing
- Zhipu probe currently fails because the account lacks balance or resource package
- No manual provider switching is required at this stage


<!-- ORIS_INSIGHT_PLATFORM:BEGIN -->
## Insight continuity anchor
后续凡涉及以下主题，优先读取：
- `docs/INSIGHT_PLATFORM_ARCHITECTURE.md`
- `docs/INSIGHT_DATA_MODEL.md`
- `docs/INSIGHT_SKILL_ROADMAP.md`
- `docs/DECISIONS/2026-04-06-insight-memory-postgres-and-skill-roadmap.md`
- `docs/ANSWER_PROTOCOL.md`
- `docs/SOURCE_POLICY.md`

后续默认约束：
- 以证据优先协议生成结论
- 报告正式件为 Word，可辅以 Excel
- 渠道下载支持 Feishu，后续支持 Qbot
- 业务常量进入 config 或数据库，不接受继续散落在脚本里
- 企业竞争力洞察采用 PostgreSQL 主库作为中台底座
<!-- ORIS_INSIGHT_PLATFORM:END -->

<!-- ORIS_INSIGHT_DB_BOOTSTRAP:BEGIN -->
## Insight database continuity
后续凡涉及企业竞争力洞察、证据链、报告生成、下载分发，优先读取：
- config/insight_storage.json
- sql/insight_schema_v1.sql
- docs/INSIGHT_DATA_MODEL.md
- docs/INSIGHT_PLATFORM_ARCHITECTURE.md
- docs/INSIGHT_SKILL_ROADMAP.md
- docs/DECISIONS/2026-04-06-postgres-insight-bootstrap.md
- docs/RUNBOOKS/INSIGHT_POSTGRES_BOOTSTRAP.md

固定约束：
- 洞察主库为 PostgreSQL
- schema 为 insight
- 连接信息走 config + secrets
- 正式报告主件为 Word
- Excel 为辅助底表
- 渠道下载支持 Feishu，后续支持 Qbot

<!-- ORIS_INSIGHT_DB_BOOTSTRAP:END -->
