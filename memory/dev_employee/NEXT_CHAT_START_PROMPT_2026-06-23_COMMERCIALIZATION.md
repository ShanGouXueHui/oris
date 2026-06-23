# Next Chat Start Prompt - Commercial Insight Employee Commercialization

Use this prompt to start a new chat without relying on previous chat history.

```text
继续 ORIS / OpenClaw / Codex-backed AI Dev Employee 项目，进入 commercial insight employee 商用化推进。

不要从头重新设计。
不要依赖聊天历史。
必须先读取 GitHub 持久化上下文和 evidence。

Repos:
- ORIS Runtime repo: https://github.com/ShanGouXueHui/oris
- Product repo: https://github.com/ShanGouXueHui/oris-commercial-insight-employee

先按顺序读取 ORIS repo：
1. docs/runtime_v2/RUNTIME_V2_FINAL_ACCEPTANCE_REPORT.md
2. memory/dev_employee/CURRENT_STATE_2026-06-23_POST_RUNTIME_V2_AND_INSIGHT_REBUILD.md
3. memory/dev_employee/ENGINEERING_GUARDRAILS_SCRIPT_AND_EVIDENCE_2026-06-22.md
4. memory/dev_employee/GUARDRAIL_MINIMAL_MANUAL_INTERVENTION_2026-06-23.md

再读取 Product repo：
1. docs/status/INSIGHT_REBUILD_STATUS_2026-06-23.md
2. docs/engineering/ENGINEERING_AND_COMMERCIALIZATION_RULES_2026-06-23.md
3. reports/testing/latest_test_result.json
4. reports/execution/insight_rebuild_module_6_execution_report.md
5. app/main.py
6. app/rebuild_api.py
7. app/domain_contracts.py
8. app/evidence_ingestion.py
9. app/brief_pipeline.py
10. app/quality_gates.py

当前事实：
- ORIS Runtime v2 A-H 已最终验收通过。
- Runtime v2 final ORIS reference: 896bdc67942a27cea98b8a4eb8f49d946795a741。
- Product Insight Rebuild Module 1-6 已通过。
- Product final reference after Module 6: 8a66d3858c42721fa44f6bae3c4a66b7140f569b。
- FastAPI version 已到 0.2.0。
- 现有 endpoint: /healthz, /healthz/details, /insights/executive-brief, /insights/rebuild/acceptance, /insights/rebuild/brief。
- 当前仍是 deterministic sample evidence；尚未接入真实 evidence source、数据库、缓存、外部模型/provider、部署 smoke test。

交互规则：
- GitHub 侧能完成的设计、文档、脚本、代码更新直接完成。
- 只有必须使用用户服务器本地环境执行测试和 push evidence 时，才给短命令。
- 不要让用户贴长日志；从 GitHub reports/execution 和 reports/testing 读取。
- 每个模块只有一个官方 bootstrap script。
- 不要创建 _v2/_v3/compat/legacy 等重复主入口。
- 不要使用 set -e。
- Git history 是备份，不用在仓库复制备份脚本。

工程规范：
- 分层解耦：API、domain contracts、evidence ingestion、brief pipeline、quality gates、orchestration/config/providers。
- 配置与业务逻辑分离。
- 外部 source/model/provider 必须通过 adapter/config 边界接入。
- 保持通用商用版本，不做单客户硬编码。
- 所有模块必须有 tests、test plan/doc、latest_test_result.json、execution_report.md 和 GitHub evidence commit。

下一步任务：
启动 Insight Rebuild Module 7: Runtime v2 Orchestration and Real Evidence Source Integration。

Module 7 建议范围：
1. product-side Runtime v2 orchestration adapter contract；
2. source connector abstraction；
3. config-separated source/model/runtime settings；
4. deterministic local source connector for tests；
5. future real web/search/model provider boundary；
6. evidence persistence plan；
7. API/runtime integration report；
8. tests and GitHub evidence。

不要直接跳到生产部署或商业收费；先完成 Module 7，把真实 evidence/source/model 的边界建立起来。
```
