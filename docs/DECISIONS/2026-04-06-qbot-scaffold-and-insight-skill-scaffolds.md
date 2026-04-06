# Decision: scaffold Qbot delivery and core insight skills before Qbot account approval

## Date
2026-04-06

## Conclusion
当前不等待 Qbot 账号审批完成，先把 ORIS 内部架构做完：
- Qbot delivery transport 先做 scaffold
- 真实执行保持 disabled，不影响 pending queue 的正常治理
- 同时落第一批 ORIS 自建 insight skill scaffold：
  - `company_profile_skill`
  - `competitor_research_skill`
  - `official_source_ingest_skill`
  - `report_build_skill`

## Why
1. 当前真正需要先固化的是 ORIS 内部交付抽象，不是单一渠道账号
2. Feishu 已验证 delivery executor 主链路，Qbot 只差渠道凭证与联调
3. 洞察与商务级 Word/Excel/PPT 生成应该以 ORIS 自有方法论为核心，不外包给第三方 skill

## Runtime decision
- `delivery.execution_channels = ["feishu"]`
- `qbot` 在 `config/report_runtime.json` 中保留为 disabled scaffold
- Qbot pending task 默认不被常规 executor 消费
- 等 QQ 开放平台审批完成后，再启用真实发送

## Skill decision
当前已建立 4 个业务 skill scaffold 与一个统一 runtime config：
- `config/insight_skill_runtime.json`
- `scripts/lib/insight_skill_runtime.py`
- `skills/company_profile_skill`
- `skills/competitor_research_skill`
- `skills/official_source_ingest_skill`
- `skills/report_build_skill`

## Artifact decision
商务级产物继续采用三层：
- Word：正式报告
- Excel：证据底表 / 评分矩阵
- PPT：管理层 / 客户汇报
