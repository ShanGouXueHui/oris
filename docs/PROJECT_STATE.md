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


## Update — 2026-04-06 Official ingest citation loop fully closed

当前状态新增结论：
- `official_source_ingest_skill` 已完成 live fetch + body extraction + `citation_link` 自动写入
- runner 输出已补齐 `citation_ids`、`written_citation_count`
- 当前 Canonical 最新一次 official ingest 已验证：
  - `analysis_run_id = 8`
  - `snapshot_id = 9`
  - `evidence_count = 8`
  - `citation_count = 8`

验证结果：
- evidence-level citation 已按 `claim_code = {run_code}:snapshot_{snapshot_id}:evidence_{evidence_id}` 自动生成
- `citation_note = auto_generated_from_official_source_ingest_skill`
- `db_write_plan` 已覆盖：
  `company / source / source_snapshot / analysis_run / evidence_item / metric_observation / citation_link`

修正说明：
- 上一版 `official_source_ingest_skill` 在 citation 输出层存在两个问题：
  - `row["title"]` 取值不稳定，导致 real run 报 `KeyError`
  - `citation_ids / written_citation_count` 未完整暴露到 runner 输出
- 当前已通过 follow-up 修复，主线以本次修正后状态为准


## Update — 2026-04-06 Account-strategy case generated and delivered

当前状态新增结论：
- `account_strategy_skill` 已完成首个真实业务 case 编排：
  `account-strategy-akkodis-huawei-cloud-auto-eu-20260406`
- 已完成 partner / cloud / customers 官方源采集，以及竞争对手 benchmark 接入
- 已生成 account-strategy 正式交付物：
  - Word
  - Excel
  - JSON
  - PPT storyline（当前环境缺少 `python-pptx`，暂未生成真实 `.pptx`）

验证结果：
- 顶层编排输出已落盘：
  `outputs/account_strategy/account-strategy-akkodis-huawei-cloud-auto-eu-20260406/.../account_strategy_case.json`
- 报告产物已接入 `insight.report_artifact`
- 可下载产物已写入 `delivery_task`
- Feishu 已完成真实发送（以 delivery_task 回写状态为准）

当前结论：
- ORIS 已具备“真实洞察 case → 证据/引用 → Word/Excel → artifact 注册 → Feishu 投递”的业务闭环
- 唯一未闭合项是：真实 `.pptx` 文件生成


## Update — 2026-04-07 Mature generic insight architecture (current target state)

目标不再是 demo/定制 case，而是可商用的高端洞察分析 AI 员工，定位对标高端咨询顾问的研究与材料输出工作流。

### 当前确认有效的主链
- `prompt_to_case_compiler.py` 已升级为 `deterministic_plus_llm_compare`
- compiler trace 当前固定包含：
  - `raw_prompt`
  - `normalized_prompt`
  - `profile_selection`
  - `deliverable_detection`
  - `question_extraction`
  - `entity_detection`
  - `role_binding_initial`
  - `role_binding_after_default_expansion`
  - `llm_compare`
  - `hybrid_merge`
  - `case_assembly`
- `company_profile` 通用链路已跑通：
  - prompt → compiled_case → official ingest / company profile → report bundle
  - 已生成 `docx / xlsx / pptx / json`
  - 已完成 artifact register + delivery executor

### 当前唯一主阻塞
- `account_strategy` 通用链路仍有 runner 入参协议不一致问题：
  - pipeline 传入的是 JSON string
  - `skills/report_build_skill/account_strategy_runner.py` 当前按文件路径读取
  - 导致 `FileNotFoundError`
- 修复原则：
  - runner 兼容两种输入：`path` 与 `inline json`
  - 后续 pipeline 可以逐步统一，但 runner 先做向后兼容，避免再次炸链路

### 商用交付口径（固定）
- Word：详细专业版洞察报告
- Excel：原始证据 / 原始出处 / 原始文本，不以抽象打分为主
- PPT：商务交流版，面向高层汇报
- 输出必须按多层框架展开，而非官网摘要再排版

### 洞察方法论（固定应用）
- BLM
- 五看：
  - 看客户
  - 看竞争
  - 看自己
  - 看产业/行业
  - 看技术
- 并强制区分：
  - 事实
  - 推断
  - 建议
  - 风险

### 当前实施策略
- 先修通用 runner / pipeline 契约
- 再提升 account_strategy 报告内容密度与原始证据底表
- 再清理重复投递与旧 trigger 噪音
- 最后再引入外部高星成熟组件做增强，不在主阻塞未清前盲目扩工具面

## Update — 2026-04-06 Generic insight pipeline delivery mode stabilized

当前状态新增结论：
- `run_generic_insight_pipeline.py` 已改为：
  - 手工调试默认“不注册 / 不投递”
  - 仅显式启用 delivery 时才注册 `report_artifact` 并执行 `delivery_executor`
- `feishu_insight_trigger.py` 已显式使用正式投递模式
- 因此当前行为已稳定为：
  - 本地/手工调试：只生成材料，不向 Feishu 重复发送
  - Feishu 自然语言触发：正式生成并自动回传 `pptx / docx / xlsx`

验证结果：
- 手工调试 `registered_count = 0`
- 手工调试 `delivery_executor_rc = None`
- Feishu 自然语言触发已成功产出并发送：
  - `account_strategy_deck.pptx`
  - `account_strategy_report.docx`
  - `account_strategy_workbook.xlsx`

已确认问题：
- 此前出现的重复发送，不是 Feishu transport 重复，而是每次重跑 pipeline 都重新注册新 delivery task 并再次执行投递
- 当前该问题已通过“调试默认不投递，触发显式投递”模式隔离

下一阶段主目标（通用化，不再 case-specific）：
1. 将 ORIS 升级为通用洞察引擎，而非单一 Akkodis case runner
2. compiler 升级为 `Rule Parser + LLM Parser + Compare/Merge` 双路解析
3. 研究框架固化为：
   - 五看（客户 / 竞争 / 自己 / 产业 / 技术）
   - BLM
   - competitive benchmark
   - value chain
   - scenario planning
4. 报告生成升级为咨询级三件套：
   - Word：详细商业洞察报告
   - Excel：原始证据与出处底表
   - PPT：商务交流版
5. 增加“外部 AI API 对比分析 + 自动优化回写”机制：
   - 比较 ORIS 输出与外部 AI 建议
   - 补齐缺失维度
   - 记录质量评估
   - 形成可演进的洞察生成闭环

明确原则：
- 不再为单个客户/单个项目写死常量
- 所有规则、实体映射、方法论、运行开关应下沉到配置文件或数据库
- 最终产品目标不是 demo，而是面向商用、接近咨询公司交付质量的高端洞察产品

