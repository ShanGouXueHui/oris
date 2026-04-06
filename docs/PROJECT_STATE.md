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


<!-- ORIS_INSIGHT_PLATFORM:BEGIN -->
## Insight platform architecture
- 已新增洞察中台总设计：`docs/INSIGHT_PLATFORM_ARCHITECTURE.md`
- 已新增洞察数据模型：`docs/INSIGHT_DATA_MODEL.md`
- 已新增洞察 skill 路线图：`docs/INSIGHT_SKILL_ROADMAP.md`
- 已新增决策记录：`docs/DECISIONS/2026-04-06-insight-memory-postgres-and-skill-roadmap.md`

### 当前固定方向
- 洞察主库：PostgreSQL
- 正式交付主件：Word
- 辅助底表：Excel
- 后续扩展：PPT
- 渠道下载：Feishu / 后续 Qbot
- 常量治理：config-first / db-first，不允许业务常量继续散落在脚本里

### 下一阶段实施顺序
1. PostgreSQL 初始化
2. 洞察 schema 落地
3. artifact 元数据统一
4. insight skill scaffold
5. Feishu / Qbot 下载分发闭环
<!-- ORIS_INSIGHT_PLATFORM:END -->

<!-- ORIS_INSIGHT_DB_BOOTSTRAP:BEGIN -->
## Insight database bootstrap
- 洞察主库已落地：PostgreSQL
- database: oris_insight
- schema: insight
- 配置文件：config/insight_storage.json
- 初始化 SQL：sql/insight_schema_v1.sql
- 决策文档：docs/DECISIONS/2026-04-06-postgres-insight-bootstrap.md
- Runbook：docs/RUNBOOKS/INSIGHT_POSTGRES_BOOTSTRAP.md

### 已落首批核心表
- company
- competitor_set / competitor_set_member
- source / source_snapshot
- evidence_item
- metric_observation
- analysis_run
- report_artifact
- citation_link
- delivery_task
- watch_task
- alert_event

<!-- ORIS_INSIGHT_DB_BOOTSTRAP:END -->
\n\n<!-- ORIS_REPORT_ARTIFACT_QUEUE:BEGIN -->
## Report artifact registry and delivery queue
- 报告产物注册已接入数据库
- 配置文件：config/report_runtime.json
- 注册脚本：scripts/register_report_delivery.py
- 目标表：
  - insight.report_artifact
  - insight.delivery_task
- 当前支持产物：
  - Word 报告
  - Excel 评分底表
  - 下载 manifest
  - zip 交付包
- 当前已排队渠道：
  - Feishu
  - Qbot
- 当前状态：
  - 已完成“产物注册 + 待分发任务入库”
  - 尚未完成“Qbot/Feishu 文件发送器消费 delivery_task”

<!-- ORIS_REPORT_ARTIFACT_QUEUE:END -->


<!-- ORIS_REPORT_DOWNLOAD_SECURITY:BEGIN -->
## Report Download Security v2
- security model: signed delivery_code
- audit table: `insight.download_event`
- duplicate pending task prevention: enabled
- revoke helper: `scripts/revoke_delivery_links.py`
- sync script: `scripts/register_report_delivery.py`
<!-- ORIS_REPORT_DOWNLOAD_SECURITY:END -->


<!-- ORIS_INSIGHT_STORAGE_COMPAT:BEGIN -->
## Insight Storage Compatibility
- normalized `config/insight_storage.json` to standard `db` block
- runtime helper now supports legacy postgres/database/storage.* shapes
- report download security v2 chain restored on top of compatible DB parser
<!-- ORIS_INSIGHT_STORAGE_COMPAT:END -->

<!-- ORIS_SESSION_WRAPUP:BEGIN -->
## Session wrap-up / continuity

- 归档总结：`docs/SESSION_WRAPUP_2026-04-06.md`
- 文档状态矩阵：`docs/DOC_STATUS_MATRIX_2026-04-06.md`
- 当前判断：系统已进入“AI员工产品化 Phase 2：证据化回答 + 报告交付 + 洞察记忆底座”阶段。
- 当前最高优先级：实现 delivery executor，把 pending delivery_task 真正发送到 Feishu / Qbot。
- 第二优先级：落地第一批 insight skills scaffold（company profile / competitor research / official source ingest / report build）。

<!-- ORIS_SESSION_WRAPUP:END -->

## Update — 2026-04-06 Feishu delivery executor live

当前状态新增结论：
- Feishu 报告下载链接分发执行器已跑通
- `insight.delivery_task` 的 Feishu pending 任务已可真实发送并回写 `sent/delivered_at`
- Feishu 发送目标使用 `chat_id`
- Feishu 发送方式使用正式 OpenAPI，而不是 webhook 直发
- 历史 `json manifest` 脏任务已识别并保留 failed，不视为当前链路失败

验证结果：
- Feishu `pending_count = 0`
- 已成功发送任务：`17 / 19 / 23 / 25 / 29 / 31`
- 历史脏任务：`21 / 27`

## Update — 2026-04-06 Qbot scaffold and insight skill scaffolds

当前状态新增结论：
- Qbot delivery 先完成 scaffold，不等待账号审批
- `delivery.execution_channels` 当前只启用 `feishu`
- Qbot 保持 disabled scaffold，避免在账号未完成前污染 pending queue
- 已创建第一批 ORIS 自建 insight skill scaffold：
  - `company_profile_skill`
  - `competitor_research_skill`
  - `official_source_ingest_skill`
  - `report_build_skill`
- 已同时建立商务级 Word / Excel / PPT 模板骨架

下一步：
- 等 Qbot 账号审批完成后启用真实发送
- 将 4 个 skill scaffold 接入真实 source/evidence/metric 写库链路

## Update — 2026-04-06 eval report script and delivery executor run wrappers

当前状态新增结论：
- `scripts/evals/run_eval_report.py` 纳入主线，作为评测结果到 Word / Excel / ZIP 报告生成脚本
- `scripts/run_delivery_executor_once.sh` 纳入主线，作为 delivery executor 单次执行入口
- `scripts/run_delivery_executor_loop.sh` 纳入主线，作为 delivery executor 常驻轮询入口

说明：
- 这 3 个文件不属于临时噪音，和当前 ORIS 的报告交付与 delivery executor 运维主线一致
- 后续若做 systemd 化，可直接复用 loop wrapper

## Update — 2026-04-06 Report-build artifacts registered and delivered

当前状态新增结论：
- `report_build_skill` 生成的 DB-backed Word / Excel / JSON 已接入 `insight.report_artifact`
- 其中可下载产物已自动创建 Feishu `delivery_task`
- Feishu 已真实发送 `canonical_db_report.docx` 与 `canonical_db_report.xlsx`
- 对应 delivery task 已回写为 `sent + delivered_at`

验证结果：
- `report_artifact` 新增：`10 / 11 / 12`
- Feishu 实发成功任务：`33 / 34`
- `report_json` 未投递，符合 `downloadable_flag=false` 设计


## Update — 2026-04-06 Official ingest now writes citation_link

当前状态新增结论：
- `official_source_ingest_skill` 已从 live fetch + body extraction 进一步闭环到 `citation_link`
- 新抓取正文级 `evidence_item` 会自动生成 evidence-level citation binding
- 当前链路已覆盖：`company → source → source_snapshot → analysis_run → evidence_item → metric_observation → citation_link`

验证结果：
- Canonical 最新 official ingest 已完成自动 citation 写入
- `citation_link` 可按 `claim_code / evidence_item_id / source_snapshot_id` 去重
- 历史 snapshot 3 的 8 条正文级 evidence 也已完成 citation 回填

