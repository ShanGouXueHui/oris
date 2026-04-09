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

## 2026-04-06 incremental handoff — report_build delivery closed loop

本轮已完成：
- `report_build_skill` 已生成本地 DB-backed `docx / xlsx / json`
- `scripts/register_report_build_delivery.py` 已可扫描 `outputs/report_build/*`
- 产物已写入 `insight.report_artifact`
- 可下载产物已写入 Feishu `delivery_task`
- `delivery_executor.py` 已将新增 report_build 任务真实发送到 Feishu
- `delivery_task 33 / 34` 已回写为 `sent`

注意事项：
- 当前闭环已覆盖：入库 → 读库组装 → 本地产物 → artifact 注册 → Feishu 投递
- `json` 产物当前不投递，符合 `downloadable_flag=false`
- 下一步应优先补 `citation_link` 与真实正文级 evidence extraction


## 2026-04-06 incremental handoff — official ingest citation_link closed loop

本轮已完成：
- `skills/official_source_ingest_skill/runner.py` 已自动写入 `citation_link`
- `scripts/backfill_citation_links_from_ingest.py` 已创建，可用于历史 ingest 补 citation
- Canonical live fetch + body extraction 最新一次运行已验证 citation 自动落库

注意事项：
- 当前 citation 是 evidence-level 绑定，`report_id` 仍为空，后续可在正式报告注册后补 report-level 绑定
- `claim_code` 当前口径：`{run_code}:snapshot_{snapshot_id}:evidence_{evidence_id}`
- 下一步应让 `report_build_skill` 直接消费 `citation_link`，生成可审计正式报告


## 2026-04-06 incremental handoff — official ingest citation output fixed

本轮已完成：
- 修复 `official_source_ingest_skill` 的 citation label/url fallback
- 修复 `total_citation_count` 初始化缺失问题
- runner 输出已增加：
  - `citation_ids`
  - `written_citation_count`
  - `db_write_plan` 中的 `citation_link`
- Canonical 最新 real run 已验证 `evidence_ids_count = 8` 且 `citation_ids_count = 8`

注意事项：
- 目前 `citation_link` 是 evidence-level 绑定，`report_id` 仍为空
- 后续应让 `report_build_skill` 直接消费 `citation_link`，形成正式报告引用层
- 当前 authoritative runtime 结论应以本次 follow-up fix 后结果为准


## 2026-04-06 incremental handoff — first account-strategy case closed loop

本轮已完成：
- `account_strategy_skill` 已升级为真实 orchestrator
- 已完成 `Akkodis + Huawei Cloud + 引望/北汽 + 欧洲竞争对手` case 编排
- 已生成 `account_strategy_case.json`
- 已生成 `account_strategy_report.docx`
- 已生成 `account_strategy_workbook.xlsx`
- 已生成 `account_strategy_bundle.json`
- 已生成 `account_strategy_deck_storyline.json`
- 已完成 artifact 注册与 Feishu 交付闭环

注意事项：
- 当前环境没有 `python-pptx`，所以 PPT 仍为 storyline JSON，不是真实 `.pptx`
- 下一步应优先补真实 PPT 生成能力
- 之后可把 `account_strategy_runner.py` 合并进 `report_build_skill` 主入口，形成统一 artifact build 路径


## 2026-04-07 incremental handoff — mature generic insight architecture

当前阶段定位：
- ORIS 洞察系统目标定位已明确为可商用高端产品，不接受 demo 级输出
- 交付目标对标高端咨询顾问材料，不是简单摘要机器人

当前确认有效：
- `compiler` 已升级为 `hybrid_compare`
- `company_profile` generic flow 已真实跑通
- 长安汽车 case 已成功输出：
  - `company_profile_report.docx`
  - `company_profile_workbook.xlsx`
  - `company_profile_deck.pptx`
  - `company_profile_bundle.json`

当前唯一主阻塞：
- `account_strategy_runner.py` 与 `run_generic_insight_pipeline.py` 的入参协议不一致
- pipeline 当前给 runner 的是 JSON string
- runner 当前按 path 读取，导致 `FileNotFoundError`

下一步固定顺序：
1. 先修 `account_strategy_runner.py`，兼容 path / inline json 双输入
2. 再跑通 Akkodis generic account strategy 全流程
3. 再收敛投递逻辑，只投递本轮新 artifact
4. 再提升 rich synthesis 与 raw evidence workbook
5. 再评估接入外部高星 skill / repo 做增强

高优先级原则：
- 常量放 config / DB，不继续写死在代码里
- 输出必须分行业层 / 技术栈层 / 客户场景层 / 竞争层 / 方案层 / 风险层
- Excel 以原始证据和出处为主，不以抽象评分为核心

## 2026-04-06 incremental handoff — generic insight delivery mode stabilized

本轮已完成：
- `run_generic_insight_pipeline.py` 已支持“手工调试默认不注册/不投递”
- `feishu_insight_trigger.py` 已改为显式开启正式投递
- Feishu 自然语言 prompt 已成功触发完整链路：
  - prompt -> compiler -> pipeline -> artifacts -> register -> delivery executor -> Feishu 回传
- 当前自然语言触发成功回传三件套：
  - `account_strategy_deck.pptx`
  - `account_strategy_report.docx`
  - `account_strategy_workbook.xlsx`

问题复盘：
- 之前出现“重复发 6 份材料”的根因，不是 Feishu 重复发，而是每次手工重跑 pipeline 都重新注册并自动投递
- 现已通过“调试默认不投递、正式触发显式投递”模式修复

下一阶段：
1. 把 ORIS 从 case-specific runner 提升为通用洞察引擎
2. compiler 升级为 `Rule Parser + LLM Parser + Compare/Merge`
3. 固化五看 / BLM / competitive benchmark / value chain / scenario planning 方法论
4. 升级三类交付件：
   - Word = 咨询级详细报告
   - Excel = 原始证据底表
   - PPT = 商务交流版
5. 增加外部 AI API 对比分析与自动优化回写机制

注意事项：
- 后续手工调试默认不应触发投递
- 只有 Feishu / 正式触发路径才允许 register + delivery
- 后续优化重点应转向“内容质量”和“通用化”，而非继续反复修触发链路


## 2026-04-07 增量记忆：必须继续推进的 3 项需求

1. 多AI结果对比 + 自动进化
- 规则路径、LLM compare、外部 AI API 建议，后续都要纳入统一 compare framework。
- compare 结果不能只停留在 compiled_case，要继续落到最终交付件。
- 目标：结构更完整、分析更深、表达更专业、证据更充分。

2. 高星 GitHub skills 纳入 ORIS 能力体系
- 持续 benchmark 洞察类、抓取类、doc/ppt 生成与美化类高星 skills。
- 对优于当前链路的能力，允许接入 ORIS 注册表与运行时。
- 原则：吸收优势实现，不做封闭自研。

3. 外部 skill refresh 进入常态化管道
- skill registry 不能静态维护，需持续刷新。
- 刷新结果要反馈到 compiler / compare / evolution / postprocess。
- 这是一项长期机制建设，不是一次性任务。

## 执行口径
- 一律按“通用版”推进，不为单一 case 写特判。
- 常量、候选集、规则、刷新配置放配置/注册表，不写死代码。
- 目标交付标准：Word 详细版、Excel 原始证据底表、PPT 交流版，质量持续向商用品质提升。

## 2026-04-07 新增刚性要求：chat_md 默认交付 + freshness 强制

1. 默认交付改为 chat_md
- 未明确要求 Word/PPT/Excel 时，默认飞书聊天里直接回复 MD 风格内容。
- 内容底部必须附来源链接。
- 手机端阅读体验优先于下载式交付。

2. 明确要求二进制交付时才生成材料
- 只有 prompt 明确要求 Word / PPT / Excel，才走文档/演示/底表交付链路。
- 否则默认 chat_md。

3. 洞察 freshness 不能忽略
- 同一主题后续再次触发时，不能无脑复用旧数据库结果。
- 当前先按保守口径：新 prompt => force_refresh + same_day_required。
- 后续继续优化为基于 DB 时间戳的细粒度 freshness 判定。

## 2026-04-07 handoff increment

### 本轮新增稳定结论
- Default delivery mode: `chat_md` unless user explicitly requests PPT/Word/Excel.
- `chat_md` reply should be mobile-friendly, directly readable in Feishu, with source links at bottom.
- Cross-day result should be re-generated by default; avoid stale reuse from prior DB-backed outputs.
- Current trigger model is single-worker sequential blocking execution, not true concurrency.
- Missing progress acknowledgment is now a confirmed UX issue; next implementation priority is staged progress messages.

### 后续实现优先级
1. Add generic progress callback for Feishu:
   - accepted
   - researching
   - synthesizing
   - delivered

2. After progress UX is stable, consider:
   - queue manager
   - parallel workers
   - task state persistence
   - retry / timeout policy

### 操作口径
- For mobile-first usage, prefer chat_md.
- For formal briefing/export scenarios, explicitly request artifact_bundle.

---

## 2026-04-07 增量交接：Oris 洞察角色继续收口方向

### 本轮确认的长期原则
- Oris 的“洞察”能力不是只做伙伴洞察，而是通用公司洞察 / 联合方案洞察 / 客户突破洞察 / 竞对洞察。
- 行业不限于汽车，设计时不要写死汽车语义。
- 用户并发发消息是正常行为，后续必须通过单实例 trigger + queue worker 解决，而不是要求用户串行操作。
- chat_md 与附件回复必须统一走同一 delivery executor，不能维持两套发送体系。
- 默认优先 chat_md 手机可读回复；只有明确要求正式材料时才走 docx / pptx / xlsx。
- 历史洞察存在老化问题；若不是同一天，应默认重跑而不是持续复用旧结论。

### 下一阶段优先级
1. 放开通用路由
   - 去掉 account_strategy 对固定角色组合的硬依赖。
   - 支持单公司洞察自动分流到 company_profile / company_insight 类 skill set。
   - 支持多主体联合洞察自动分流到通用 account_strategy。

2. 统一发送链路
   - chat_md 注册为统一 delivery task。
   - delivery executor 同时支持文本消息与附件消息。
   - 生产链路不再直接依赖独立 sender 脚本。

3. 单实例 + 排队
   - trigger 增加 lock。
   - trigger 只负责入队。
   - worker 负责逐条执行 pipeline。
   - message_id / case_code / chat_id 必须可追踪。

4. freshness
   - 同 case 但跨天：默认重新洞察。
   - 同天且 prompt 高相似：允许复用或增量刷新。
   - 用户明确要求“最新”时，强制重跑。

### 已知报错样本（后续定位参考）
- `account_strategy profile requires detected partner and cloud_vendor`
- `missing FEISHU_APP_ID/FEISHU_APP_SECRET (or LARK_*)`
- `register_report_build_delivery.py: error: unrecognized arguments: --report-prefix ...`


<!-- SESSION_HANDOFF_2026_04_08_FEISHU_ENTITY_PROVIDER_START -->
## Session Handoff — 2026-04-08 — Feishu insight worker / company entity detection / provider env recovery

### 1. 本项目固定定位
ORIS = Operational Reasoning & Integration System。
它不是聊天玩具，而是一个面向执行、具备推理能力、可整合多模型与多工具的 AI 研发员工系统。

后续所有新对话都必须先从 GitHub 仓库读取并学习以下入口文件，再开始编码或排障：
- AGENT.md
- AGENTS.md
- MEMORY.md
- BOOTSTRAP.md
- TOOLS.md
- USER.md
- docs/PROJECT_STATE.md
- docs/MODEL_POLICY.md
- docs/CHANGELOG_AGENT.md
- docs/ANSWER_PROTOCOL.md
- docs/SOURCE_POLICY.md
- docs/ROUTING_POLICY.md
- docs/CONFIG_GOVERNANCE.md
- docs/PROVIDER_ORCHESTRATION.md
- memory/HANDOFF.md

如果新对话遇到“当前现象”和“docs/代码描述”不一致，必须：
1. 先以 GitHub 仓库中的代码和 docs 为准进行对比；
2. 再判断是运行态漂移、临时补丁未提交，还是 docs 过期；
3. 严禁脱离仓库记忆直接重写。

### 2. 本轮已确认的系统现状
#### 2.1 Feishu 发送链路
- Feishu sender 已恢复可用。
- 之前 ack / final_send 失败的根因之一，是 `.env` 被误缩成仅剩 FEISHU_APP_ID / FEISHU_APP_SECRET，导致其他 provider key 丢失。
- `.env.runtime` 曾存在，但 `.env` 不完整；后来 env 已重建。

#### 2.2 Provider orchestration
- Provider orchestration 已恢复运行。
- 已验证以下脚本能够正常执行并产出：
  - `scripts/quota_probe.py`
  - `scripts/provider_scoreboard.py`
  - `scripts/model_selector.py`
- `orchestration/active_routing.json` 已能正常生成。
- 当前 routing 结果显示：
  - `primary_general -> openrouter/auto`
  - `free_fallback -> qwen3.6-plus`
  - `coding -> qwen-coder-turbo-0919`
  - `cn_candidate_pool -> qwen3.6-plus`

#### 2.3 环境变量状态
- Feishu 保持不变。
- 已重新补齐或恢复：
  - OPENROUTER_API_KEY
  - HF_TOKEN / HUGGINGFACE_HUB_TOKEN
  - DASHSCOPE_API_KEY / BAILIAN_API_KEY
  - GEMINI_API_KEY / GOOGLE_API_KEY
  - ZHIPU_API_KEY / ZHIPUAI_API_KEY
  - HUNYUAN_SECRET_ID / HUNYUAN_SECRET_KEY
  - TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY
- 后续禁止再把 provider key 写死到代码里；只能从 `.env` / `.env.runtime` / 配置文件 / 数据库读取。

#### 2.4 Worker 运行面
- 曾出现多个 `insight_queue_worker.py` 实例并发，根因是：
  - 老的 loop launcher `scripts/run_insight_queue_worker_loop.sh`
  - 手工 nohup 启动
  - lock file 只能防并发启动，不能阻止外部 respawn
- 已识别出 loop launcher，并已禁用旧脚本副本：
  - `scripts/run_insight_queue_worker_loop.sh.disabled`
  - `scripts/run_insight_queue_worker_loop.sh.bak_*`
- 目标状态应始终保持：**只允许 1 个 worker 实例**。

### 3. 当前真正卡住的问题
#### 3.1 不是 Feishu 发送问题
Feishu 现在能收到消息，但收到的是：
- prompt 被加工后的占位内容；
- 或 profile / bootstrap 占位内容；
- 或渲染异常提示；
而不是真正的公司洞察正文。

#### 3.2 真正根因：company entity detection / target_company binding 失真
`company_profile` 主链路里，目标公司识别不稳定，典型问题：
- `n8n` / `dify` / `Akkodis` 有时能识别；
- `引望` 会错误命中为 `华为云`；
- 更糟时，行业词如 `AI Agent` 会被误识别成 company entity；
- 导致上游 official ingest 落库的是错误实体或空实体；
- 后续 `source_snapshot_count / evidence_count / metric_count` 为 0；
- renderer 只能输出 bootstrap 占位内容或阻断说明。

换言之：**当前最优先问题不是继续雕正文模板，而是先把“通用公司识别能力”上线到主链路。**

### 4. 后续工作的优先级（必须按顺序）
#### P0：先修 company entity detection 主链路
目标：
- 让 `company_profile` 在进入主流程前，先运行一个通用 detector；
- detector 优先识别“用户真正要求洞察的单一公司主体”；
- 严禁把行业概念、能力名词、竞品集合、场景描述识别为公司。

要求：
1. 不写死常量到代码；
2. 规则、阈值、provider_order 放在独立配置文件，至少在 `config/`；
3. 可以有 fallback，但 fallback 也必须配置化；
4. 识别结果要带：
   - `target_company`
   - `confidence`
   - `method`
   - `reason`
5. 主链路仅在 confidence 达标时覆盖原 `target_company`；
6. 若识别失败，要显式阻断，并给出结构化错误，不允许继续产出垃圾正文。

#### P1：把 detector 接进 `run_generic_insight_pipeline.py`
要求：
- `company_profile` 类型进入 pipeline 时，先做 precheck；
- precheck 成功才继续 official source ingest；
- precheck 失败则直接返回明确错误；
- worker log 中必须增加：
  - `precheck`
  - `detected_target_company`
  - `detection_confidence`
  - `detection_method`

#### P2：修正文聊天版渲染
前提是 P0 / P1 先完成。
要求：
- Feishu 最终发送的必须是“真实洞察正文”；
- 不是 prompt；
- 不是 `company_profile_skill DB-backed profile ready...` 这种占位语；
- 不是 bootstrap checklist；
- 不是失败提示，除非真的阻断。

#### P3：回写 docs / memory
修完后，必须同步更新：
- docs/PROJECT_STATE.md
- memory/HANDOFF.md
- docs/CHANGELOG_AGENT.md
必要时新增一个 DECISIONS 文档，记录：
- 为什么引入通用 entity detector
- 为什么禁止行业概念误识别成公司
- 为什么 company_profile 必须先做 precheck

### 5. 编程规范（必须继续遵守）
1. 常量不要写死在代码里，写到配置文件、数据库或 env。
2. 不要让我手工找文件、手工改代码；要给 copy-paste 可执行命令。
3. 改代码前先读 GitHub docs 和记忆文件，再出 plan。
4. 改代码时先备份，再修改，再自检，再验证。
5. 不要用临时补丁掩盖主问题；优先做可复用、可配置、可回写 docs 的正式解法。
6. 任何“看起来省事”的临时方案，如果会污染主链路，就不要上。
7. 遇到异常，先区分：
   - 识别问题
   - 配置问题
   - provider 问题
   - 渲染问题
   - Feishu transport 问题
   不要混为一谈。
8. 后续若需要引入外部 skill / 开源组件，先比较：
   - 是否真能提升主链路
   - 是否可配置
   - 是否不会覆盖现有 provider orchestration
   - 是否能留下 docs 和记忆

### 6. 新对话第一目标
新对话的唯一第一目标是：

**把“通用公司识别能力”正式上线到 ORIS 主链路，并通过 Feishu 发送出真实公司洞察正文。**

在这个目标完成前，不要继续做花哨优化，不要继续堆模板，不要继续修饰 prompt。
<!-- SESSION_HANDOFF_2026_04_08_FEISHU_ENTITY_PROVIDER_END -->

## 2026-04-08 drift triage and governance tightening
本轮已完成：
- 正式补充 GitHub 同步治理、实体识别治理、洞察投递治理文档
- 增强 `ROUTING_POLICY / CONFIG_GOVERNANCE / PROVIDER_ORCHESTRATION`
- `.gitignore` 正式纳管 runtime 日志 / lock / out 文件
- 运行日志文件开始退出 Git 索引，避免继续污染主仓库

当前固定判断：
- 主阻塞仍是 company entity detection，不是 Feishu transport
- `active_routing.json` 是生成型基线快照，不应随每次运行噪音式提交
- Feishu 聊天链路必须只发送真实正文或明确阻断提示，不得再发送 prompt / bootstrap / placeholder

当前漂移分类：
- keep-mainline：
  - `config/company_entity_detection.json`
  - `config/company_focus_config.json`
  - `config/entity_resolution.json`
  - `config/insight_delivery_config.json`
  - `scripts/build_company_focus_prompt.py`
  - `scripts/company_entity_detector.py`
  - `scripts/feishu_insight_enqueue.py`
  - `scripts/insight_queue_worker.py`
  - `scripts/render_mobile_insight.py`
- hold-experimental：
  - `scripts/feishu_account_strategy_trigger.py`
  - `scripts/run_account_strategy_case_pipeline.py`
  - `scripts/run_account_strategy_trigger_loop.sh`
  - `scripts/run_insight_queue_worker_loop.sh.disabled`
- drop-from-git：
  - `orchestration/*.jsonl`
  - `orchestration/*.lock`
  - `orchestration/*.out`
  - `orchestration/restore_provider_files.json`

下一步固定顺序：
1. 正式接入通用 company entity detection 到 mainline compiler / pipeline
2. 清理旧 direct-send / placeholder 路径
3. 本地自检
4. Feishu 实测
5. 再更新 docs / handoff / decisions


## 2026-04-08 company entity mainline — stabilized
本轮已完成：
- `company_entity_detector.py` 正式接入 company_profile 主链路
- 识别顺序已调整为：
  - `registry_alias`
  - `regex_fallback`
  - `llm_arbitration`
  - `gliner`
- 当前默认禁用本地 GLiNER
- `llm_arbitration` 已接入 `scripts/oris_infer.py`
- `llm_arbitration.role` 当前使用 `cn_candidate_pool`
- compare 请求与行业概念请求均已前置阻断
- `run_generic_insight_pipeline_plus.py` 在 blocked 场景直接短路返回
- `insight_queue_worker.py` 只发送真实正文或阻断提示
- pipeline 内 direct send 已退出主链路

已验证：
- `Anthropic` 单公司请求可正常通过
- `Akkodis` / `引望` 别名识别可正常通过
- `AI Agent 行业现在怎么样` 会阻断
- `比较华为云和阿里云谁更强` 会阻断

当前固定判断：
- 当前真正可用的商用主方案，不是强依赖本地 GLiNER
- 当前机器配置下，应优先使用 alias / regex / LLM arbitration
- 若后续要重新启用本地 GLiNER 作为正式增强层，应先升级机器配置

已知后续项：
- compiler_trace 仍保留 upstream v2 的历史 entity_detection 痕迹
- compare 扩展链路的 `llm_compare.api_key_not_found` 当前不阻塞 entity precheck 主链路，可后续单独治理\n\n<!-- FREE_MODEL_ROUTING_HANDOFF:START -->
## Free model routing handoff (2026-04-09)
- 继续处理 ORIS 免费 AI API / 免费模型治理时，先读：
  - `docs/FREE_MODEL_ROUTING_ARCHITECTURE_2026-04-09.md`
  - `docs/RUNBOOK_FREE_MODEL_ROUTING_2026-04-09.md`
  - `docs/DECISIONS/2026-04-09-free-model-routing-contract-drift.md`
- 当前已确认：
  - free eligibility 有效，至少包含 `qwen3.6-plus`
  - runtime execute 的 provider secrets 映射已覆盖 openrouter / gemini / zhipu / alibaba_bailian / tencent_hunyuan
  - `free_fallback` 正常，`report_generation` 仍可能先打 `openrouter/auto`
- 当前定性：
  - 主问题是 policy -> runtime_plan 契约漂移
  - 不是“免费 provider 全部失效”
- 后续修复顺序：
  1. 先修 free-only role 在 runtime_plan 中的严格过滤
  2. 再修 free eligibility / provider health / scoreboard 的自动刷新链
  3. 再修 402/429/missing_api_key 下的 free failover 执行纪律
<!-- FREE_MODEL_ROUTING_HANDOFF:END -->\n

<!-- FREE_MODEL_ROUTING_FINAL_HANDOFF:START -->
## Free model routing final handoff (2026-04-09)
- 当前 HEAD 已验证：
  - `report_generation` 自动走 `qwen3.6-plus -> alibaba_bailian`
  - preflight / postflight refresh 已生效
- 修复关键提交：
  - `6485853` refresh active routing before inference
  - `00a09e5` restore stable infer refresh chain
- 中间提交 `4dbb629`、`a3db6a4` 为过渡态，不应作为最终实现口径
- 后续若继续增强，优先方向是：
  1. `runtime_execute.py` 失败分类治理
  2. `runtime_state.json` block / recover 细化
  3. free eligibility 自动扩容与恢复策略
<!-- FREE_MODEL_ROUTING_FINAL_HANDOFF:END -->
