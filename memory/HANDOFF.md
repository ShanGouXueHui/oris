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
\n\n<!-- ORIS_REPORT_ARTIFACT_QUEUE:BEGIN -->
## Report artifact continuity
后续凡涉及 Word / Excel 报告产物、下载分发、报告注册，优先读取：
- config/report_runtime.json
- scripts/register_report_delivery.py
- docs/DECISIONS/2026-04-06-report-artifact-registry-and-delivery-queue.md
- docs/RUNBOOKS/REPORT_ARTIFACT_DELIVERY.md

固定约束：
- 常量放配置文件或数据库，不散落脚本
- 正式报告主件为 Word
- Excel 为辅助底表
- 报告产物先入 report_artifact，再建 delivery_task
- 下载分发渠道当前排队支持 Feishu / Qbot

<!-- ORIS_REPORT_ARTIFACT_QUEUE:END -->


<!-- ORIS_REPORT_DOWNLOAD_SECURITY:BEGIN -->
## Report Download Security v2
- delivery link is now delivery_code scoped
- audit / revoke / max_downloads supported
- future enhancement can add recipient binding if needed
<!-- ORIS_REPORT_DOWNLOAD_SECURITY:END -->


<!-- ORIS_INSIGHT_STORAGE_COMPAT:BEGIN -->
## Insight Storage Compatibility
- current runtime expects normalized `db` config but remains backward-compatible
- do not assume a single config shape when adding future storage/report helpers
<!-- ORIS_INSIGHT_STORAGE_COMPAT:END -->

<!-- ORIS_SESSION_WRAPUP:BEGIN -->
## Session wrap-up / next-chat entry

新对话进入后，先读：
1. `docs/PROJECT_STATE.md`
2. `memory/HANDOFF.md`
3. `docs/SESSION_WRAPUP_2026-04-06.md`
4. `docs/DOC_STATUS_MATRIX_2026-04-06.md`

当前要继续的第一件事：
- 等 Qbot 账号审批完成后启用真实发送。
- 将 4 个 insight skill scaffold 接入真实 source / evidence / metric 写库链路。

注意事项：
- 用 copy-paste 可执行命令
- 不使用 set -e
- 不手工改文件
- 先验证，再 commit/push
- 优先读 GitHub 文档，不依赖聊天短上下文

<!-- ORIS_SESSION_WRAPUP:END -->

## 2026-04-06 incremental handoff — Feishu delivery executor

本轮已完成：
- `config/report_runtime.json` 增加 delivery/channels/channel_targets 配置
- `scripts/register_report_delivery.py` 开始写入默认 `channel_target`
- `scripts/delivery_executor.py` 已按真实 `insight.delivery_task` 表结构改造
- Feishu 通过 `scripts/feishu_send_executor_skeleton.py` 正式发送下载链接消息成功
- Feishu 当前无剩余 pending delivery_task

注意事项：
- `channel_target` 对 Feishu 当前口径为 `chat_id`
- 历史任务 `21 / 27` 为非 downloadable json manifest，已做 historical_cleanup 标注
- 下一步优先补 Qbot executor，然后开始 4 个 insight skill scaffold

## 2026-04-06 incremental handoff — Qbot scaffold and insight skills

本轮已完成：
- `config/report_runtime.json` 增加 qbot disabled scaffold 与 execution_channels
- `scripts/qbot_send_executor_skeleton.py` 已创建
- `config/insight_skill_runtime.json` 已创建
- 已创建 4 个 ORIS insight skill scaffold
- 已创建 Word / Excel / PPT 模板骨架

注意事项：
- `qbot` 当前是 scaffold，不做真实发送
- 审批完成后只需补 webhook/target 配置并启用 execute_enabled
- 后续应优先把 4 个 skill 接到真实 DB 写入与 artifact generation

## 2026-04-06 incremental handoff — eval report and executor wrappers

本轮已完成：
- `scripts/evals/run_eval_report.py` 已确认纳入主线
- `scripts/run_delivery_executor_once.sh` / `scripts/run_delivery_executor_loop.sh` 已确认纳入主线

注意事项：
- `run_eval_report.py` 是当前评测报告生成脚本，不是临时测试文件
- `run_delivery_executor_loop.sh` 适合后续 systemd / cron / supervisor 化接入
