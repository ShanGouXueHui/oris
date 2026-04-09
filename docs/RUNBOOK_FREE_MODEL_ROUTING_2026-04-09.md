# ORIS 免费模型失效排查 Runbook（2026-04-09）

## 1. 适用场景
当出现以下任一现象时，执行本 runbook：
- 明明配置了免费模型，但执行时先打到收费 provider
- `execution_log.jsonl` 出现 `402 Payment Required`
- free_fallback 正常，但业务角色仍走 paid primary
- 自动 failover 存在，但没有先严格用 free-only

## 2. 排查顺序

### 第 1 层：先确认设计意图
必读文档：
- `docs/PROJECT_STATE.md`
- `memory/HANDOFF.md`
- `docs/PROVIDER_ORCHESTRATION.md`
- `docs/FREE_MODEL_ROUTING_ARCHITECTURE_2026-04-09.md`

### 第 2 层：确认配置基线
必看文件：
- `orchestration/routing_policy.yaml`
- `orchestration/free_eligibility.json`
- `orchestration/provider_registry.json`
- `orchestration/provider_health_snapshot.json`
- `orchestration/provider_scoreboard.json`
- `orchestration/runtime_plan.json`
- `orchestration/active_routing.json`
- `orchestration/runtime_state.json`

重点检查：
1. 目标 role 是否显式配置：
   - `ordered_candidates`
   - `allow_free_candidates_only`
2. `free_eligibility.json` 是否真的包含可用 free model
3. `runtime_plan.json` 中目标 role 的：
   - `selected_model`
   - `execution_primary`
   - `failover_chain`
4. `runtime_state.json` 是否存在 block / degraded 影响

### 第 3 层：确认代码真实行为
必看代码：
- `scripts/runtime_plan.py`
- `scripts/runtime_execute.py`
- `scripts/oris_infer.py`
- `scripts/model_selector.py`
- `scripts/quota_probe.py`
- `scripts/provider_scoreboard.py`

重点检查：
1. `runtime_plan.py` 是否真正按 role rules 过滤 free-only
2. `model_selector.py` 的 free-only 规则，是否与 runtime_plan 对齐
3. `runtime_execute.py` 是否覆盖目标 provider 的 secret 读取路径
4. `oris_infer.py` 是否在执行前刷新了 runtime plan

### 第 4 层：区分故障类型
#### A. secret 问题
特征：
- `missing_api_key`
- 某 provider 永远不执行
- plan 中存在，execute 时直接跳过

#### B. provider 问题
特征：
- 429 / 5xx / timeout
- health snapshot degraded
- scoreboard 排名异常下滑

#### C. free policy 失效
特征：
- role 已声明 free-only
- 但 `execution_primary` 仍是收费模型

#### D. runtime_plan 生成错误
特征：
- `runtime_plan.json` 已经错了
- 还没进入 execute 就已选错模型

#### E. runtime_execute 执行错误
特征：
- plan 正确
- execute 时顺序、provider、secret、retry 行为与 plan 不符

### 第 5 层：最小修复原则
1. 先修 plan，不先重写 execute
2. 先修契约，不先扩展 provider
3. 先保证 free-only 严格执行，再做 free pool 自动扩容
4. 不破坏 company_profile / 其他已稳定角色主链

## 3. 当前已确认结论
截至 2026-04-09：
- free eligibility 至少包含 `qwen3.6-plus`
- `free_fallback` 可成功选到 `qwen3.6-plus`
- `report_generation` 仍可能选到 `openrouter/auto`
- 当前主问题是：
  - **role policy 没有被 runtime plan 严格贯彻**
