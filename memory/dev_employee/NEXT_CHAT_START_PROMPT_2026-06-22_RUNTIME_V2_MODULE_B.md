继续 ORIS / OpenClaw / Codex-backed AI Dev Employee 项目。

不要从头重新设计。不要依赖聊天历史。必须先读取 GitHub 仓库 `ShanGouXueHui/oris` 的持久化上下文。

## 必读顺序

1. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-22_AUTONOMOUS_RUNTIME_V2.md`
2. `memory/dev_employee/ENGINEERING_GUARDRAILS_SCRIPT_AND_EVIDENCE_2026-06-22.md`
3. `reports/testing/latest_test_result.json`
4. `reports/execution/module_A_execution_report.md`
5. `docs/runtime_v2/ARCHITECTURE_AND_STATE_MACHINE_MODULE_A.md`
6. `schemas/runtime_v2/state_machine.schema.json`
7. GitHub issue #15: `Acceptance Project: ORIS Autonomous Dev Employee Runtime v2`

## 当前状态

Runtime v2 Module A 已通过：

- final commit: `c244e2467fe153377b370df0ffc35d541b8b3ef1`
- evidence commit: `a785cef3fb7fd5b5f3403a568d1e701a9e72ac13`
- latest test status: `passed`

## 下一步

继续 Runtime v2 Module B：Persistent Run Store and Queue Contract。

Module B 必须产出：

- persistent run record model
- queue item contract
- state transition function/API
- append-only event log semantics
- idempotency and recovery rules
- tests for enqueue, claim/dequeue, state transition validation, terminal-state protection, event persistence
- `docs/testing/MODULE_B_TEST_PLAN.md`
- `reports/testing/module_B_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_B_execution_report.md`

## 强制提醒

必须遵守 `ENGINEERING_GUARDRAILS_SCRIPT_AND_EVIDENCE_2026-06-22.md`：

- 每个 workflow 只允许一个官方可执行入口。
- 不要创建 `_v2.sh`、`_v3.sh`、`compat.sh`、`legacy.sh` 等并行兼容脚本。
- Git 历史就是备份，不要额外保留可执行备份脚本。
- 要求用户重新执行脚本前，先从 GitHub 验证官方脚本状态。
- 终端只输出短摘要，长日志写入 `reports/execution/`。
- 后续由 assistant 从 GitHub 读取报告和日志，不要求用户粘贴长日志。
- ORIS 平台验证不得修改产品仓库，除非任务明确要求。

## 第一响应要求

输出：已读取摘要、当前完成/未完成、guardrail 已遵守情况、Module B 最小执行方案、短命令。不使用 `set -e`。
