继续 ORIS / OpenClaw / Codex-backed AI Dev Employee 项目。

不要从头重新设计。
不要依赖聊天历史。
必须先读取 GitHub 仓库 ShanGouXueHui/oris 的持久化上下文，再继续执行。

GitHub Repo:
https://github.com/ShanGouXueHui/oris

按顺序读取：

1. memory/dev_employee/CURRENT_STATE_2026-06-22_AUTONOMOUS_RUNTIME_V2.md
2. memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-22_AUTONOMOUS_RUNTIME_V2.md
3. docs/DEV_EMPLOYEE_AUTONOMOUS_RUNTIME_V2_ACCEPTANCE_2026-06-22.md
4. docs/OPERATING_CONTEXT_AND_ENGINEERING_RULES_2026-06-22_RUNTIME_V2.md
5. docs/DEV_EMPLOYEE_FINAL_ACCEPTANCE_2026-06-22.md
6. memory/dev_employee/CURRENT_STATE_2026-06-22_POST_ACCEPTANCE.md
7. orchestration/project_registry.json
8. memory/dev_employee/current_task.json
9. memory/dev_employee/current_task.md
10. GitHub issue #15: Acceptance Project: ORIS Autonomous Dev Employee Runtime v2

同时读取产品仓库当前状态：

Product repo:
https://github.com/ShanGouXueHui/oris-commercial-insight-employee

重点核验：

- Module 0 commit: 7d1d604b92b21f1213f990140b3345b4be2163ca
- Module 1 是否已经有后续 commit；如果没有，不要继续扩展旧 interactive insight product。

当前战略方向：

ORIS 不是一个需要人盯着维护的脚本堆，而是要升级成一个持续自运转的 AI 开发员工底座。

目标：

OpenClaw Web 只作为控制面，用于下发目标、查看状态、审批高风险动作。真正执行必须由 ORIS 后台 autonomous worker / agent loop 完成，不依赖浏览器、不依赖终端、不依赖长聊天上下文。

优先级：

1. 停止继续扩展旧的 interactive insight product 任务。
2. 启动 ORIS Autonomous Dev Employee Runtime v2 验收项目。
3. 先做 Runtime v2 Module A：Architecture and State Machine Design。
4. Runtime v2 完成后，再由升级后的 ORIS 重新构建 insight 能力作为端到端验收项目。

Module A 必须产出：

- architecture document
- state machine schema
- failure taxonomy
- acceptance criteria
- tests for status transitions
- docs/testing/MODULE_A_TEST_PLAN.md
- reports/testing/module_A_test_result.json
- reports/testing/latest_test_result.json
- reports/execution/module_A_execution_report.md

工程规则：

- 直接修改 GitHub 或通过 ORIS/Codex 执行后提交 GitHub。
- 不要依赖聊天上下文作为记忆。
- 每个模块都必须有测试计划、测试结果 JSON、执行报告、commit SHA。
- 不要把业务产品代码写入 ORIS；ORIS 只做平台、运行时、治理、证据、编排。
- insight 产品代码在 ShanGouXueHui/oris-commercial-insight-employee。
- 遵守分层解耦、配置分离、一个主流 main 分支、通用商用版本原则。
- 不要使用 set -e。
- 不要提交私密配置或凭证类文件。
- 下载 skills 必须 quarantine、manifest/source validation、smoke test 后才能使用。
- 只有凭证、付费资源、生产高危操作、破坏性数据库操作、合规/安全风险、重复不可恢复失败才允许人工阻塞。

当前操作阻塞：

上一轮远程执行 bootstrap 未成功，原因是运行环境缺少对应远程访问凭证。这不是 ORIS 代码失败，而是操作环境访问问题。下一步需要用户在有访问权限的执行环境中继续，或通过已经具备执行能力的 ORIS/OpenClaw Web 下发 Runtime v2 Module A。

你的第一步输出：

1. 已读取文档摘要；
2. 当前已完成/未完成事项；
3. 远程访问阻塞判断；
4. Runtime v2 Module A 的最小可执行方案；
5. 若需要命令，给 copy-paste 命令，不使用 set -e。

不要说“我不知道历史”。历史已写入 GitHub，必须从 GitHub 读取。
