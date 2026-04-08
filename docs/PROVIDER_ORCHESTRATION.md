# Provider Orchestration Module v2

## 1. Goal
Build a provider orchestration layer for ORIS that can:
- discover candidate model sources
- probe availability and quota status
- route by role (`primary_general`, `report_generation`, `coding`, `cn_candidate_pool`, `free_fallback`)
- retry first, then fail over automatically
- keep runtime decisions machine-readable and auditable

---

## 2. File roles
### Policy / source-of-truth inputs
- `orchestration/routing_policy.yaml`

### Generated registry / scoring / runtime outputs
- `orchestration/provider_registry.json`
- `orchestration/provider_health_snapshot.json`
- `orchestration/provider_scoreboard.json`
- `orchestration/runtime_plan.json`
- `orchestration/active_routing.json`

### Supporting scripts
- `scripts/quota_probe.py`
- `scripts/provider_scoreboard.py`
- `scripts/model_selector.py`
- `scripts/runtime_execute.py`
- `scripts/oris_infer.py`
- `scripts/oris_http_api.py`

---

## 3. Design principles
1. 不把任何“免费政策”当永久事实
2. 区分：
   - provider registry
   - routing policy
   - health snapshot
   - score layer
   - runtime plan
   - active routing
3. Secret 统一通过 SecretRef / secrets store 管理
4. provider 宣传口径不等于 runtime 可用性
5. 所有替换、降级、临时封禁都要机器可读

---

## 4. Source of truth hierarchy
### 路由规则真源
- `routing_policy.yaml`

### 当前已确认运行基线
- `active_routing.json`

### 观测与评分中间层
- `provider_health_snapshot.json`
- `provider_scoreboard.json`
- `runtime_plan.json`

解释：
- `active_routing.json` 可以作为当前运行基线，但不是“每次 probe 都自动要提交的文件”
- health / scoreboard / runtime_plan 更偏运行观测层，默认不作为人工长期记忆

---

## 5. Commit policy
### 可提交
- 路由规则变化
- selector 逻辑变化
- 经验证的 `active_routing.json` 基线重置

### 默认不提交
- 每次 probe 导致的 health snapshot 波动
- 临时失败记忆
- 一次性 provider 恢复文件
- 纯运行态诊断产物

---

## 6. Runtime behavior
- 先 retry
- 再 failover
- 记录连续失败
- 临时封禁异常候选
- 使用 block-aware execution primary
- 写入 execution logging

---

## 7. 商用品质要求
- 用户不应感知 provider 抖动
- failover 必须有边界，不能跨任务类型乱跳
- 任何自动选择结果都应可追溯到 policy + health + score + plan
