# ORIS 新对话启动 Prompt（2026-04-08）

你现在接手 ORIS（Operational Reasoning & Integration System）项目的继续开发与排障工作。

先不要急着写代码。先完整学习 GitHub 仓库中的记忆和设计文件，再开始执行：
仓库地址：
https://github.com/ShanGouXueHui/oris

你必须优先读取并学习以下文件，把它们视为本轮工作的最高优先级上下文来源：
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

工作要求：
1. 先从 GitHub md 文件完全学习 ORIS 整体设计；
2. 先从 GitHub md 文件完全学习当前问题、当前状态、待完成工作；
3. 如果遇到无法处理或现象不一致，务必对比 GitHub oris 仓库中的代码与 docs 描述，确认是运行态漂移、临时补丁未提交、还是 docs 已过期；
4. 严格遵守历史上已定下的编程规范：
   - 常量不要写死在代码里，写在配置文件、数据库或 env；
   - 不要让我手工找文件、手工改代码；
   - 输出必须 copy-paste 可执行；
   - 改代码前先出 plan；
   - 修改后必须自检、验证；
   - 先备份，再修改，再验证，再决定是否提交 docs；
   - 不要再用临时补丁掩盖主问题。

你需要先从 memory/HANDOFF.md 中重点学习以下事实：
- Feishu sender 已恢复；
- provider orchestration 已恢复，active_routing 正常；
- .env / .env.runtime 中 provider key 已重建；
- 当前真正卡点不是 Feishu 发送，而是 company_profile 主链路中的 target_company / company entity detection 失真；
- 典型错误是把行业概念（如 AI Agent）识别成公司，或把“引望”误识别成“华为云”；
- 这会导致 official ingest 落库错误实体或空实体，最终 renderer 只能输出占位内容或阻断提示；
- 当前第一优先级不是继续雕聊天正文模板，而是先把“通用公司识别能力”正式上线到主链路。

本轮任务唯一第一目标：
把“通用公司识别能力”正式接入 ORIS 主链路，并通过 Feishu 正常发送出真实公司洞察正文，而不是 prompt、bootstrap 占位文、渲染异常提示或空洞察。

你需要按这个顺序推进：
P0：先审查当前仓库里 company_profile / entity detection / pipeline / render / worker 相关代码和配置；
P1：给出最小但正式的改造方案，把通用 company entity detection 上线到主链路；
P2：确保 detector 配置化，不写死常量；
P3：确保识别失败时明确阻断，不再产出垃圾正文；
P4：本地自检 + Feishu 端实测；
P5：更新 docs/PROJECT_STATE.md、memory/HANDOFF.md、必要时新增 DECISIONS 文档。

输出方式要求：
- 先给我一个简洁 plan；
- 然后给我一组一组 copy-paste 命令；
- 每组命令后告诉我该贴什么结果给你；
- 不要让我自己推断下一步；
- 不要让我手工打开编辑器改文件；
- 不要跳过验证步骤。

另外，请特别检查：
- 当前 worker 是否还有多实例风险；
- 当前旧 loop launcher 是否已经彻底退出主链路；
- `run_generic_insight_pipeline.py`、`run_generic_insight_pipeline_plus.py`、renderer、worker 之间是否仍存在“发送 prompt / 发送占位文”的旧逻辑；
- 当前 company entity detection 是否仍有 alias_match 误判、行业词抢占、竞品列表污染主实体的问题。

从读取 GitHub md 和记忆开始，不要直接写代码。


## 2026-04-08 governance addendum
进入新对话后，除原有必读文件外，还必须优先读取：
- `docs/GITHUB_SYNC_POLICY.md`
- `docs/ENTITY_DETECTION_POLICY.md`
- `docs/INSIGHT_DELIVERY_POLICY.md`
- `docs/DECISIONS/2026-04-08-github-sync-and-entity-detection-governance.md`

额外要求：
- 先判断 worktree 漂移属于：主链路候选 / 运行噪音 / 实验残留
- 不允许把 jsonl / lock / out 这类 runtime 文件继续带进主链路提交
- `active_routing.json` 只在基线变更被验证后提交
- Feishu 聊天链路只允许发送真实正文或阻断提示
- company entity detection 失败时必须明确阻断


## 2026-04-08 company entity mainline addendum
进入新对话后，继续 ORIS 公司洞察链路时，必须优先知道以下事实：

- 当前公司识别主链路已正式切为：
  - `registry_alias`
  - `regex_fallback`
  - `llm_arbitration`
  - `gliner`
- 当前默认禁用本地 GLiNER
- `llm_arbitration` 通过 `scripts/oris_infer.py` 调用，当前 role 为 `cn_candidate_pool`
- 单公司请求可放行；行业概念 / 多公司比较请求应阻断
- `run_generic_insight_pipeline_plus.py` 已支持 blocked 场景直接短路返回
- `insight_queue_worker.py` 只发送真实正文或阻断提示
- 当前已知尾项：compiler_trace 中仍保留 upstream v2 的历史 entity_detection 痕迹，但不阻塞主链路
