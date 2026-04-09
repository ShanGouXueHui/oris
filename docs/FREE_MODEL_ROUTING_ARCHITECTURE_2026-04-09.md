# ORIS 免费 AI API / 免费模型路由架构说明（2026-04-09）

## 1. 目的与范围
本文档沉淀 ORIS 中“免费 AI API Token / 免费模型路由 / failover / secrets 读取 / runtime 执行”的当前设计、真实行为、已确认问题与后续修复方向，作为后续新对话与研发续接的 authoritative memory。

## 2. 当前链路总览
ORIS 当前免费模型运行链路，按职责可分为以下几层：

1. policy 层  
   - `orchestration/routing_policy.yaml`
   - 定义各 role 的候选模型顺序、规则限制、是否只允许 free candidates。

2. registry / health / scoreboard 层  
   - `orchestration/provider_registry.json`
   - `orchestration/provider_health_snapshot.json`
   - `orchestration/provider_scoreboard.json`

3. free eligibility 层  
   - `orchestration/free_eligibility.json`
   - 表达“当前经过验证的免费模型集合”。

4. planning 层  
   - `scripts/runtime_plan.py`
   - 读取 policy / health / free eligibility / runtime state，生成 `orchestration/runtime_plan.json`

5. selection 层  
   - `scripts/model_selector.py`
   - 参与 role -> model 的策略选择与 active routing 结果生成。

6. execute 层  
   - `scripts/runtime_execute.py`
   - 根据 `runtime_plan.json` 的 `execution_primary` 与 `failover_chain` 执行真实 provider 调用。

7. infer orchestration 层  
   - `scripts/oris_infer.py`
   - 先刷新 runtime plan，再调用 runtime execute，执行完成后再做 plan refresh，并写 execution log。

8. feedback / state 层  
   - `orchestration/runtime_state.json`
   - `orchestration/execution_log.jsonl`
   - `scripts/runtime_feedback.py`（若启用）

## 3. 当前 source of truth
当前这条链不是单一真源，而是分层真源：

- 路由规则真源：`orchestration/routing_policy.yaml`
- 免费模型集合真源：`orchestration/free_eligibility.json`
- provider / model 基线真源：`orchestration/provider_registry.json`
- 当前计划真源：`orchestration/runtime_plan.json`
- 执行事实真源：`orchestration/execution_log.jsonl`

工程上应遵循：
- policy 决定“应该如何选”
- runtime plan 决定“本轮准备怎么跑”
- execution log 决定“实际发生了什么”

## 4. 当前已确认的真实基线
截至 2026-04-09，已确认：

### 4.1 free eligibility
`orchestration/free_eligibility.json` 当前结构中：
- `verified_free_models = ["qwen3.6-plus"]`

说明当前 free pool 不是空的。

### 4.2 runtime execute provider secret 映射
`scripts/runtime_execute.py` 当前已覆盖以下 provider 的 secrets 路径映射：
- openrouter
- gemini
- zhipu
- alibaba_bailian
- tencent_hunyuan

secrets 文件路径为：
- `~/.openclaw/secrets.json`

### 4.3 role 当前实际行为
通过 runtime plan 与 execution log 观察到：
- `free_fallback -> qwen3.6-plus`
- `cn_candidate_pool -> qwen3.6-plus`
- `report_generation -> openrouter/auto`

说明：
- 免费链路基础设施存在且可运行
- 但并不是所有目标角色都被严格约束到 free-only

## 5. 当前已确认故障现象
### 5.1 典型故障
`report_generation` 角色执行奔驰飞书请求时：
- `selected_model = openrouter/auto`
- `execution_primary = openrouter/auto`
- 首发请求曾返回：
  - `HTTP Error 402: Payment Required`
- 随后回退到 Gemini 成功

### 5.2 后续 smoke 补充事实
2026-04-09 手工 smoke test 中，`report_generation` 仍直接使用：
- `openrouter/auto`
- 且本次 openrouter 直接成功返回

这说明：
- 当前并不是“openrouter 恒定不可用”
- 而是 `report_generation` 角色仍未被强制绑定到免费候选链

## 6. 当前最关键的问题定性
当前主问题不是：
- free provider 全部失效
- secret 全部失效
- failover 全部失效

当前主问题是：
- **免费治理机制已存在，但没有被强约束地贯彻到所有目标角色**
- **policy 与 runtime plan 之间存在契约漂移**

## 7. 设计目标（后续修复目标）
后续免费模型治理应达到以下目标：

1. 自动更新  
   - 自动刷新 free eligibility / provider health / scoreboard / runtime plan

2. 自动启用备份  
   - 当前 free primary 不可用时，自动切到下一 free candidate

3. 自动排除收费  
   - 当 role 配置为 free-only 时：
     - runtime plan 不得产出收费 execution_primary
     - failover chain 也不得混入收费模型

4. 可追溯  
   - 能解释每次为何选到该模型、为何切换、为何 block、为何降级

## 8. 当前结论
当前 ORIS 在免费 AI API / 免费模型方面：
- 已具备基础设施
- 已具备 secret 映射
- 已具备 runtime execute 与 failover
- 已具备至少一个实跑 free model：`qwen3.6-plus`

但系统尚未完成：
- 角色级 free-only 的严格治理
- 自动排除收费候选
- free eligibility 的全自动扩容与稳定刷新
