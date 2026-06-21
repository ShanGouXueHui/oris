# Next Chat Start Prompt — Insight Product — 2026-06-22

Use this prompt to continue in a new chat.

```text
继续 ORIS / OpenClaw / Codex-backed AI Dev Employee 项目，进入正式 Insight Product / 商业洞察员工开发。

不要从头重新设计。
不要依赖聊天历史。
必须先读取 GitHub 仓库 ShanGouXueHui/oris 的持久化上下文，再继续。

GitHub Repo:
https://github.com/ShanGouXueHui/oris

按顺序读取：

1. docs/DEV_EMPLOYEE_FINAL_ACCEPTANCE_2026-06-22.md
2. memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-22.md
3. docs/INSIGHT_PROJECT_KICKOFF_2026-06-22.md
4. docs/OPERATING_CONTEXT_AND_ENGINEERING_RULES_2026-06-22.md
5. memory/dev_employee/CURRENT_STATE_2026-06-22_POST_ACCEPTANCE.md
6. memory/dev_employee/NEXT_CHAT_START_PROMPT_2026-06-22_INSIGHT.md
7. orchestration/project_registry.json
8. scripts/lib/insight_db.py
9. scripts/lib/insight_db_config.py
10. scripts/lib/insight_db_records.py
11. scripts/lib/insight_db_schema.py
12. scripts/lib/insight_db_utils.py
13. scripts/dev_employee_runtime/bridge_runner.py
14. scripts/dev_employee_runtime/bridge_codex.py
15. scripts/dev_employee_runtime/bridge_evidence.py
16. scripts/dev_employee_task_states.py

当前事实：

- ORIS Dev Employee 最终验收已通过。
- 验收任务：demo-openclaw-web-task-board-20260622015615
- final verdict: status_accept=true, terminal=true, has_product_commit_sha=true, has_evidence_files=true
- Product Commit SHA: 9ccff8fcef6eb8ef08597183eb16fb235f1f7b59
- OpenClaw Web read-only status 已验证 terminal=true。

当前目标：

基于历史 ORIS insight 设计和代码资产，开发一个正式的商业洞察员工产品。目标工作风格类似高端咨询顾问：洞察公司情况、市场结构、竞对格局、财务质量、产品能力、战略信号、风险和情景判断，并输出证据支撑的管理层简报。

边界：

- ORIS 仓库只做平台编排、Dev Employee、注册表、治理和证据。
- 新业务产品代码必须放在独立产品仓库。
- 默认产品仓库：ShanGouXueHui/oris-commercial-insight-employee
- 默认本地路径：/home/admin/projects/oris-commercial-insight-employee
- 默认 project key：oris-commercial-insight-employee

交互规则：

- 使用中文，职业化、直接、结构化。
- 直接读写 GitHub，不要让用户手工粘贴长日志。
- Linux copy-paste 命令不要使用 set -e。
- 命令分小步，日志写入 logs/ 或 /tmp，只 tail 关键内容。
- 编码遵守分层解耦、配置分离、平台/产品分离、单一主线分支、可商用通用版本。
- 如果已有历史 insight 代码有价值，先审计再利旧；没有价值可以明确标记为废弃并重建。

第一阶段 Phase 0 任务：

1. 审计历史 insight 资产：scripts/lib/insight_db*.py、相关 docs、历史 commit 线索。
2. 判断哪些资产复用、重构、迁移、废弃。
3. 创建或准备独立产品仓库 oris-commercial-insight-employee。
4. 搭建最小 FastAPI 服务。
5. 添加 Pydantic insight request/response 模型。
6. 添加一个 stub workflow：company profile 或 executive brief。
7. 添加 pytest 覆盖：health、health details、一个 insight endpoint。
8. 写 migration report。
9. 若产品 repo 本地和远端都存在，更新 ORIS project_registry.json。
10. 通过 ORIS Dev Employee pipeline 完成 commit、push、evidence、status 验证。

开始后先输出：

- 当前已读文档摘要；
- 历史 insight 资产判断；
- Phase 0 技术方案；
- 本轮要让 Dev Employee 执行的具体 task objective；
- 是否需要先创建产品仓库。
```
