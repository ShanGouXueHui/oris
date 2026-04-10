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


## 2026-04-07 增量记忆：通用洞察引擎下一阶段 3 项刚性需求

### 1) 多AI对比与自动进化能力必须纳入通用主链路
ORIS 后续在生成报告内容、结构、结论与材料表达时，不能只依赖单一路径输出；必须支持：
- 将规则编译结果与外部 AI API 结果进行对比；
- 对比维度至少包括：结构完整性、行业展开深度、技术栈分层、客户场景覆盖、竞争分析充分度、证据充分度、表达专业度；
- 将对比后的升级建议沉淀为 evolution actions，并尽量 materialize 到最终 docx / xlsx / pptx 成品中；
- 目标不是“多模型并列展示”，而是“自动择优、自动吸收、自动进化”，让 ORIS 输出质量持续提升。

### 2) 高星 GitHub insight / Word / PPT skills 要纳入能力基线
ORIS 不能只依赖当前自研实现；必须建立外部成熟能力对标机制：
- 持续关注并引入 GitHub 上高星、成熟、业界常用的洞察分析、信息抓取、Word 生成、PPT 生成、美化排版等 skills / libraries / toolchains；
- 对这些外部能力进行 benchmark，对比当前 ORIS 自研链路的优劣；
- 对有明确优势的外部能力，允许通过配置、注册表、适配器方式接入 ORIS；
- 原则不是“为了接而接”，而是“吸收更优方法、结构、版式、工程实践”，提升商用品质。

### 3) 外部 skill 更新刷新要进入 ORIS 常态化需求管道
外部高星 skills 更新很快，不能一次接入后长期静态使用；必须将 skill refresh 机制纳入 ORIS 通用需求管道：
- 建立 external skill registry refresh 能力；
- 支持周期性刷新候选 skill 的版本、活跃度、适配性、价值判断；
- 将 refresh 结果反馈给 compiler / compare / evolution / postprocess 链路；
- 后续设计原则：把“外部能力更新换代”视为 ORIS 的常规输入，而不是一次性项目动作。

### 补充原则
- 以上三项必须按照“通用能力”建设，不能继续为单一 case 特判；
- 所有新增常量、候选 skill、路由规则、刷新配置，优先放配置文件或注册表，不写死在代码；
- 商业目标维持不变：ORIS 要向可商用高端咨询产品演进，对标专业咨询顾问交付质量，而非 demo 或玩具系统。

## 2026-04-07 增量记忆：默认交付改为聊天 MD + 洞察 freshness 强制口径

### 1) 默认交付方式调整
- 若用户 prompt 未明确要求 Word / PPT / Excel 交付物，则 ORIS 默认不发送下载型材料。
- 默认改为在飞书对话中直接回复 chat_md 风格内容，便于手机端快速查看。
- chat_md 输出要求：
  - 有结构化标题与分段内容；
  - 覆盖执行摘要、行业/竞争、技术栈、客户场景、建议动作、风险提示等；
  - 最下方附数据来源链接。
- 只有在用户明确要求 Word / PPT / Excel 时，才走二进制材料交付链路。

### 2) Freshness / 重洞察口径
- 用户第二次或后续再次发送 prompt 时，不能默认长期复用旧数据库内容。
- 当前阶段先采用保守口径：新 prompt 触发时，明确向下游传递 same_day_required / force_refresh。
- 后续再继续优化为：比较数据库中相关 evidence/source_snapshot/analysis_run 的时间戳，若非当天则自动重洞察，若当天且满足 freshness 条件才允许复用。
- 核心原则：数据库是能力沉淀层，不是无限期静态答案缓存层；洞察内容会老化，必须考虑 freshness。

### 3) 交付体验优先级
- 手机端阅读体验优先级提升。
- 能在飞书聊天里直接读完的内容，优先不要让用户下载文件。
- 下载型交付用于正式汇报、外发、归档、演示等明确场景。

## 2026-04-07 Feishu chat_md default + freshness + progress UX

### 新增结论
1. Generic insight 默认交付策略已调整为：
   - 若用户未明确要求 Word / PPT / Excel，则默认走 `chat_md`
   - 结果直接回复到飞书聊天框，底部附数据来源链接
   - 只有在用户明确要求正式报告/底表/汇报材料时，才走 `artifact_bundle`

2. Freshness 策略明确：
   - 若同一 case 的已有结果不是当天生成，则默认重新洞察
   - 不应长期复用旧数据库结论，避免内容老化
   - 后续应把“按天强制重跑”沉淀为统一 runtime policy

3. 当前 Feishu insight trigger 的执行模型仍为：
   - 单进程
   - 顺序消费
   - 阻塞式 pipeline 执行
   因此多条 prompt 同时发送时，不是并发生成，而是串行排队执行

4. 当前用户体验短板已明确：
   - 飞书前台不会天然显示 thinking / 生成中
   - 若中间没有状态回执，长耗时任务会表现为“看起来没反应”

### 下一步优化优先级
1. 为 generic insight 增加进度回执：
   - 已收到
   - 正在检索资料
   - 正在生成结论
   - 已完成发送

2. 长期再考虑：
   - 队列化
   - 真正并发 worker
   - task status registry
   - 可视化状态查询

### 当前建议使用方式
在进度回执未上线前，飞书侧更适合一次发一条洞察请求，等待回复后再发下一条，以避免用户误判为未处理。

---

## 2026-04-07 - Oris 洞察角色通用化与发送链路收口

### 新增设计结论
1. **Oris 洞察角色从“伙伴洞察”升级为“通用公司洞察 skill set”**
   - 不再局限于 partner / cloud_vendor 固定组合。
   - 需要兼容：
     - 单公司洞察（如：引望、Akkodis、某零售公司）
     - 联合方案洞察（如：Akkodis + 华为云）
     - 客户突破洞察（如：联合搞定目标客户）
     - 竞对洞察 / 行业洞察
   - 行业不限于汽车，也应可覆盖零售等其他行业。

2. **用户并发发消息是默认假设，不是异常行为**
   - 不能假设用户会等待上一条完成再发下一条。
   - 后续必须改为：
     - 单实例 trigger
     - queue / worker 串行消费
     - message_id 级别去重
     - 不丢任务、不互相覆盖、不依赖人工控制节奏

3. **chat_md 与附件回复必须统一走同一 delivery executor**
   - 不能长期保留双发送链路。
   - chat_md 也应注册为统一 delivery task，由同一 executor 发送。
   - 避免再次出现：
     - 独立 sender 缺少 FEISHU_APP_ID / FEISHU_APP_SECRET
     - 附件能发、chat_md 不能发
     - 日志与回执链路割裂

### 当前阶段默认产品策略
1. **默认手机可读**
   - 用户未明确要求 Word / PPT / Excel 时，默认输出 chat_md。
   - chat_md 需适合飞书聊天场景直接阅读，底部附 source links。

2. **正式汇报再输出附件包**
   - 用户明确要求正式汇报版 / 下载版 / 对外材料时，再生成 docx / pptx / xlsx。

3. **洞察 freshness 必须考虑跨天老化**
   - 若历史洞察不是同一天，默认重新洞察。
   - 不能长期复用旧数据库结论充当“最新结论”。

### 已暴露问题（需在后续实现中消除）
1. account_strategy 路由仍出现对 `partner + cloud_vendor` 的硬依赖，导致单公司洞察失败。
2. chat_md 发送链路曾直接依赖 `send_feishu_text_message.py`，与附件链路不一致。
3. artifact 注册脚本接口口径存在不一致，出现 `--report-prefix` 参数不兼容问题。
4. trigger 允许重复启动，存在多实例并发读写风险。


## Update — 2026-04-08 Governance tightening
当前状态新增结论：
- GitHub 现被再次明确为 ORIS 的权威长期记忆与主链路代码来源
- 已补充：
  - `docs/GITHUB_SYNC_POLICY.md`
  - `docs/ENTITY_DETECTION_POLICY.md`
  - `docs/INSIGHT_DELIVERY_POLICY.md`
  - `docs/DECISIONS/2026-04-08-github-sync-and-entity-detection-governance.md`
- `.gitignore` 已正式接管 runtime 日志 / lock / out 等运行噪音治理
- `active_routing.json` 继续保留为“可跟踪但需审慎提交”的已验证基线快照
- 当前第一优先级仍然不是继续雕聊天模板，而是把通用 company entity detection 正式接入主链路，并确保识别失败时明确阻断

当前漂移治理口径：
- 应进入主链路评审：
  - `config/company_entity_detection.json`
  - `config/company_focus_config.json`
  - `config/entity_resolution.json`
  - `config/insight_delivery_config.json`
  - `scripts/build_company_focus_prompt.py`
  - `scripts/company_entity_detector.py`
  - `scripts/feishu_insight_enqueue.py`
  - `scripts/insight_queue_worker.py`
  - `scripts/render_mobile_insight.py`
- 暂不纳入本轮主链路：
  - `scripts/feishu_account_strategy_trigger.py`
  - `scripts/run_account_strategy_case_pipeline.py`
  - `scripts/run_account_strategy_trigger_loop.sh`
  - `scripts/run_insight_queue_worker_loop.sh.disabled`
- 明确属于运行噪音：
  - `orchestration/*.jsonl`
  - `orchestration/*.lock`
  - `orchestration/*.out`
  - `orchestration/restore_provider_files.json`


## Update — 2026-04-08 Company entity mainline stabilized
本轮已完成 company_profile 主链路的正式收口：

### 主链路结果
- `company_entity_detector.py` 已接入正式主链路
- 当前识别顺序为：
  - `registry_alias`
  - `regex_fallback`
  - `llm_arbitration`
  - `gliner`
- 当前默认禁用本地 GLiNER
- `llm_arbitration` 当前通过 `scripts/oris_infer.py` 调用，role 使用 `cn_candidate_pool`

### 当前行为
- 单公司请求可放行，例如：
  - `Anthropic`
  - `Akkodis`
  - `引望`
- 行业概念请求会阻断，例如：
  - `AI Agent 行业现在怎么样`
- 多公司比较请求会阻断，例如：
  - `比较华为云和阿里云谁更强`

### 聊天链路行为
- pipeline 在 blocked 场景直接返回 `blocked=true`
- worker 只发送真实正文或明确阻断提示
- pipeline 内 direct send 已退出正式主链路
- 当前不会再继续向 Feishu 发送 prompt / bootstrap / placeholder 占位正文

### 当前资源判断
- 当前部署机（2C2G / 1.6GiB 内存）不适合作为 GLiNER medium 的稳定线上主依赖
- 当前更合适的线上策略是 alias / regex / LLM arbitration
- 若后续要重新启用本地 GLiNER 作为正式增强层，推荐升级到至少 `4C8G`，更建议 `4C16G`

### 已知尾项
- compiler 的主输出面已清理 blocked 场景下的 target_company / detected_entities
- `compiler_trace` 中仍保留 upstream v2 的历史 entity_detection 痕迹，属于已知后续优化项，不阻塞当前主链路发布\n\n<!-- FREE_MODEL_ROUTING_STATUS:START -->
## Free model routing status (2026-04-09)
- ORIS 已建立免费模型运行链路：routing_policy -> free_eligibility -> runtime_plan -> runtime_execute -> execution_log。
- 当前 `free_eligibility.json` 已确认包含 `verified_free_models = ["qwen3.6-plus"]`。
- 当前 `free_fallback` 与 `cn_candidate_pool` 已可选到 `qwen3.6-plus`，说明免费链路基础设施存在且可运行。
- 当前主要问题不是“免费 API 全坏”，而是 `report_generation` 等角色尚未被严格治理为 free-only，仍可能先选到 `openrouter/auto`。
- 当前问题定性为：policy 与 runtime plan 之间的契约漂移。
- 详见：
  - `docs/FREE_MODEL_ROUTING_ARCHITECTURE_2026-04-09.md`
  - `docs/RUNBOOK_FREE_MODEL_ROUTING_2026-04-09.md`
  - `docs/DECISIONS/2026-04-09-free-model-routing-contract-drift.md`
<!-- FREE_MODEL_ROUTING_STATUS:END -->\n

<!-- FREE_MODEL_ROUTING_FINAL_STATUS:START -->
## Free model routing final status (2026-04-09)
- `report_generation` 已验证自动切到免费主链：`qwen3.6-plus -> alibaba_bailian`
- `oris_infer.py` 当前执行链已升级为：
  - preflight: `quota_probe.py` / `provider_scoreboard.py` / `model_selector.py` / `runtime_plan.py`
  - execute: `runtime_execute.py`
  - postflight: 同链路 best-effort refresh
- 当前 smoke 验证结果：
  - `preflight_warnings = []`
  - `post_refresh_warnings = []`
- 当前说明：免费模型机制已从“人工纠偏”升级为“执行时自动纠偏”
- 详见：
  - `docs/DECISIONS/2026-04-09-infer-preflight-refresh-free-routing.md`
  - `docs/FREE_MODEL_ROUTING_ARCHITECTURE_2026-04-09.md`
  - `docs/RUNBOOK_FREE_MODEL_ROUTING_2026-04-09.md`
<!-- FREE_MODEL_ROUTING_FINAL_STATUS:END -->

<!-- RUNTIME_ROUTING_GOVERNANCE_STATUS:START -->
## Runtime routing governance status (2026-04-09)
- `runtime_execute.py` 已完成失败分类治理，当前会将失败映射为：
  - `missing_key`
  - `priced_out`
  - `rate_limited`
  - `provider_unstable`
  - `execution_error`
- 分类结果会写回 `orchestration/runtime_state.json`，当前已确认新增/维护字段包括：
  - `last_error_class`
  - `last_provider_id`
  - `blocked_until`
  - `last_failure_at`
  - `last_success_at`
  - `consecutive_failures`
- 当前 smoke 验证保持通过：
  - `report_generation -> qwen3.6-plus -> alibaba_bailian`
- 当前说明：免费模型模块已从“自动刷新 + 自动执行”升级到“自动刷新 + 自动执行 + 失败治理”
- 详见：
  - `docs/DECISIONS/2026-04-09-runtime-state-failure-classification.md`
  - `docs/DECISIONS/2026-04-09-infer-preflight-refresh-free-routing.md`
  - `docs/FREE_MODEL_ROUTING_ARCHITECTURE_2026-04-09.md`
<!-- RUNTIME_ROUTING_GOVERNANCE_STATUS:END -->

<!-- ORIS_CAPABILITY_UPGRADE_PLAN:START -->
## ORIS capability upgrade plan (2026-04-09)
- 内容层升级方向：从高价值段落洞察，升级到指标序列 + 行业参数 + 跟踪KPI体系
- 交付层升级方向：从 bullet-style ppt，升级到商务模板化 deck（cards / kpi dashboard / risk matrix / tracking dashboard）
- 外部 skills 采用策略：
  - adopt now: agent-browser, chain-of-density, shelv, pdf-generation
  - keep in-house: evidence scoring, metric normalization, consulting storyline
- 详见：
  - docs/ORIS_SKILL_ADOPTION_PLAN_2026-04-09.md
  - config/company_metric_taxonomy.json
  - config/presentation_theme.json
<!-- ORIS_CAPABILITY_UPGRADE_PLAN:END -->
