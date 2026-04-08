# DECISION — 2026-04-08 company entity mainline with LLM arbitration

## Status
Accepted

## Context
ORIS 的公司洞察主链路存在以下问题：
- target_company / entity detection 经常把行业概念、竞品、合作方误识别为主实体
- Feishu 发送层已恢复，但真正主阻塞不是 transport，而是 company binding 失真
- 本地 GLiNER medium 在当前 2C2G / 1.6GiB 内存机器上不适合作为稳定主依赖
- 识别失败时必须阻断，不能继续生成占位正文或垃圾洞察

## Decision
1. 正式将 company entity detection 接入 company_profile 主链路
2. 当前主识别顺序调整为：
   - registry_alias
   - regex_fallback
   - llm_arbitration
   - gliner
3. 默认禁用本地 GLiNER：
   - 保留配置
   - 不作为当前线上主依赖
4. 启用 `llm_arbitration`：
   - 走 `scripts/oris_infer.py`
   - role 使用 `cn_candidate_pool`
   - 通过现有 provider orchestration 执行
5. compare 请求与行业概念请求继续前置阻断
6. company_profile blocked 时：
   - 清空 `detected_entities`
   - 清空 `role_bindings.target_company`
   - pipeline 直接返回 blocked payload
   - worker 只发送明确阻断提示，不发送占位正文
7. Feishu 发送职责保持单点：
   - worker 为唯一发送口
   - pipeline 内 direct send 退出主链路

## Why this decision
- 当前机器资源不足以稳定承载 GLiNER medium 作为线上主依赖
- alias / regex / LLM arbitration 组合更适合当前商业化推进阶段
- 该方案比“继续硬扛本地模型”更稳、更可维护、更容易在 GitHub 中固化

## Consequences
### Positive
- company_profile 主链路已有正式 precheck
- 行业概念 / 比较请求可在前置阶段阻断
- Feishu 不再继续发送 prompt / placeholder / 空洞察
- ORIS 在当前机器配置下也可继续推进商用闭环

### Trade-offs
- 当前仍依赖免费模型池的可用性做 llm_arbitration
- GLiNER 未完全退出，只是当前默认禁用
- compiler_trace 中仍可能保留 upstream v2 的历史痕迹，但不影响主输出口径

## Known follow-ups
1. 将 compiler upstream 的历史 `entity_detection` 痕迹进一步收敛
2. 视机器资源情况决定是否在更高配置机器上重新启用本地 GLiNER
3. 后续可为 llm_arbitration 增加更严格的 schema validation / audit logging
