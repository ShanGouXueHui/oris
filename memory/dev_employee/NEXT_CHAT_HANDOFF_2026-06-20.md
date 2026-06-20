# ORIS / OpenClaw / Codex-backed AI Dev Employee — Next Chat Handoff

## Use

The current conversation is near a practical context limit.

Paste the startup prompt below into a new conversation. The new conversation must read GitHub durable context before planning or execution and must not reconstruct project truth from old chat history.

## Completed predecessor

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Result:

`ENABLED_READONLY_AUTOMATIC_ACCEPTED`

Evidence commit:

`65217d4bb81f4ac3cd8c6d917af95425d2b47529`

Checks:

- 26/26 PASS;
- Routing Skill installed and visible;
- three ORIS tools passed native natural-language acceptance;
- telemetry privacy passed;
- queue and product unchanged;
- rollback not required;
- no product task;
- no write tool.

## Current task

Task id:

`commercial-openclaw-typed-write-actions-20260620`

Status:

`readonly_p0_completed_latency_baseline_v1_persisted_typed_write_actions_design_pending`

Current step:

`new_chat_audit_current_main_then_reconcile_and_implement_offline_typed_write_action_foundation`

## Current runtime truth

- Native OpenClaw UI and native sessions remain the commercial primary interface.
- Plugin `oris-dev-employee` `0.1.0` is installed.
- Routing Skill `oris-readonly-status` is installed and visible to Agent `main`.
- Policy mode is `profile-authority-preserved+created-profile-also-allow+skill-unrestricted`.
- `oris_queue_status`, `oris_task_status` and `oris_latest_task_status` are enabled and accepted.
- Typed lifecycle telemetry is privacy-safe.
- Initial latency baseline v1 is persisted.
- No generic exec/write tool is enabled.
- No typed write action is registered or enabled.
- No product task is active.
- Production host `8.136.28.6` remains out of scope.

## Startup prompt

```text
继续 ORIS / OpenClaw / Codex-backed AI Dev Employee 商用化项目。

不要从头重新设计，不要依赖旧聊天上下文，不要脱离 GitHub 现有体系另起炉灶。必须先读取 GitHub 仓库 `ShanGouXueHui/oris` 的持久化上下文。

GitHub Repo：
https://github.com/ShanGouXueHui/oris

当前对话已经完成 read-only P0。不要再把 runtime 误判为 tools-denied，也不要重复 effective-surface、provider/model capability 或三工具 enablement 诊断。

请按顺序读取：

1. `memory/dev_employee/CONTEXT_INDEX_ADDENDUM_2026-06-20.md`
2. `memory/dev_employee/CONTEXT_INDEX.md`
3. `memory/dev_employee/CURRENT_STATE_2026-06-20.md`
4. `memory/dev_employee/SESSION_ARCHIVE_COMPLETION_2026-06-20.md`
5. `memory/dev_employee/ENVIRONMENT_AND_WORKING_CONTEXT_2026-06-20.md`
6. `memory/dev_employee/current_task.json`
7. `memory/dev_employee/current_task.md`
8. `docs/DEV_EMPLOYEE_READONLY_P0_COMPLETION_AND_LATENCY_BASELINE_2026-06-20.md`
9. evidence commit `65217d4bb81f4ac3cd8c6d917af95425d2b47529`
10. `docs/DEV_EMPLOYEE_TYPED_WRITE_ACTIONS_COMMERCIAL_PHASE_PLAN_2026-06-20.md`
11. `docs/DEV_EMPLOYEE_NATIVE_SKILL_SUPPORT_TOOL_CONTRACT_2026-06-20.md`
12. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
13. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
14. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`
15. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_CORRECTION_2026-06-20.md`
16. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-19.md`
17. `orchestration/project_registry.json`
18. `memory/dev_employee/SESSION_ARCHIVE_2026-06-20.md` 仅在需要追溯早期失败历史时读取。

读取完成后，先简要总结：

- 当前固定架构；
- read-only P0 已完成能力；
- Plugin、Routing Skill、三个 typed read-only tools 和 hooks 状态；
- 当前保留的 runtime policy；
- 初始 privacy-safe latency baseline；
- 当前 write capability 状态；
- 原始商用任务中仍未完成的事项；
- 当前任务目标；
- 下一步最小安全动作；
- 后续商用优先级。

然后直接继续执行，不要重新设计整个系统，不要让我决定日常工程细节。

当前任务：

- task id：`commercial-openclaw-typed-write-actions-20260620`；
- 目标：设计并实现通用、受控、可审计的 typed write actions 离线基础；
- 必须包含 approval、RBAC、project authorization、risk tier、immutable prepared operation、idempotency、atomic task/queue transaction、cancel、explicit terminal retry、privacy-safe audit；
- 当前阶段只允许设计和 offline implementation；
- write actions 必须保持未注册、未启用；
- 禁止提交真实产品任务；
- 禁止使用 generic exec、shell 或 file-write tool 作为商业入口。

第一优先级：先对当前 `main` 做完整 code-first audit，再修改代码。

重点检查并修复：

1. 重复定义函数、类、变量和模块绑定；
2. 重复 parser、validator、policy、profile expansion；
3. 重复 service helper、rollback helper、evidence publisher、entrypoint；
4. competing authority；
5. duplicate function bodies；
6. import cycles；
7. oversized mixed-responsibility modules；
8. hardcoded project/path/host/port/branch/provider/model/runtime/version/acceptance special case；
9. legacy execution paths；
10. config/code separation 和 contract errors。

不要通过 scanner allowlist 隐藏真实问题。一个规则只保留一个权威实现。大文件必须按 schema/domain、policy、runtime adapter、service control、validation、evidence、entrypoint 分层解耦。

代码门必须达到：

RESULT=CODE_AUDIT_PASS
DUPLICATE_BINDINGS=0
AUTHORITY_VIOLATIONS=0
DUPLICATE_FUNCTION_BODIES=0
IMPORT_CYCLES=0
OVERSIZED_MODULES=0
FORBIDDEN_HARDCODING=0
LEGACY_PATH_FINDINGS=0
CONTRACT_ERROR=

代码门通过后：

1. 全面检查现有 task lifecycle、queue、project registry、authorization、idempotency、Plugin、Agent Harness 和 evidence 实现；
2. 先确定每个规则现有的唯一 authority，不要新增平行实现；
3. 将 `docs/DEV_EMPLOYEE_TYPED_WRITE_ACTIONS_COMMERCIAL_PHASE_PLAN_2026-06-20.md` 与现有代码对齐；
4. 实现最小通用 offline foundation；
5. 增加 schema、RBAC allow/deny matrix、project authorization、risk tier、approval replay/expiry/separation、idempotency、atomic transaction、cancel/retry、concurrency 和 privacy 测试；
6. 配置与代码分离；
7. 不注册或启用 write actions；
8. 不访问或修改生产；
9. 不改变已验收的 read-only policy、Plugin tools 或 Routing Skill；
10. 通过 GitHub 提交代码、测试、设计和 evidence。

当前不可逆产品决策：

1. `https://control.orisfy.com` 主界面是 OpenClaw 原生 UI 和原生会话体系；
2. 自研 ORIS Web Console 仅保留受限 `/admin` 和回滚/诊断路径；
3. 正式链路：用户 → OpenClaw 原生 UI → 原生 ORIS Plugin / Agent Harness → ORIS 授权与任务治理 → Codex 真实代码执行 → 产品提交、测试和 ORIS evidence 返回 OpenClaw；
4. 不重新安装或升级 OpenClaw；
5. 复用现有 `openclaw-gateway.service` 和 `127.0.0.1:18789`；
6. 不恢复大范围 Prompt 关键词匹配创建任务；
7. ORIS 通过稳定 typed tools/actions/plugins 接入 OpenClaw；
8. 18891 和 18892 不得公网暴露；
9. 产品代码、测试和文档留在独立产品仓库；
10. `main` 是唯一主流分支；
11. ZenMux 排除，除非明确重新开放。

环境：

- 开发/控制/执行机：`43.106.55.255`，用户 `admin`；
- ORIS：`/home/admin/projects/oris`；
- 产品：`/home/admin/projects/oris-final-acceptance-api`；
- 产品 baseline：`bcb93e17ea88704548101f5e4a5c460e15a80ec7`；
- 生产机：`8.136.28.6`，用户 `deploy`，不要触碰；
- OpenClaw：`2026.5.19 (a185ca2)`；
- Gateway：`127.0.0.1:18789`；
- Free Mesh：loopback `8789`；
- enqueue/status：`127.0.0.1:18891`；
- Intake：`127.0.0.1:18892`；
- Web Console：`127.0.0.1:18893`；
- PostgreSQL：`oris_insight` / schema `insight`，仅用于 research/insight，与 Dev Employee task state 分离；
- Provider/Model 是 runtime fact，不允许在通用代码中硬编码。

交互和工程方式：

- 使用中文，职业化、直接、结构化；
- 不要让我决定日常工程细节；
- 你能直接完成的 GitHub 工作直接完成；
- 长脚本、文档和补丁直接写入 GitHub；
- 需要服务器执行时只给一条短命令运行 GitHub 中的脚本；
- 不要给长 heredoc；
- 详细日志写入 `logs/dev_employee/` 并从 GitHub 查询；
- 每个执行脚本最后只输出一个 `===== SUMMARY =====`；
- GitHub、Summary 和聊天不得输出敏感配置、认证信息、raw session id、conversation content、tool args/results 或 private marker；
- Linux 用户脚本不要使用 `set -e`；
- 配置与代码分离；
- 可以备份和使用 detached worktree，但不创建竞争性长期分支；
- 构建通用商用版本，不为验收项目硬编码特例；
- 完成必须验证真实交付物、测试、commit SHA、remote SHA 和 GitHub evidence；
- 不要在 commit 后继续追加同一个 tracked log。

后续商用优先级：

1. 当前 `main` 新一轮代码治理归零；
2. typed write actions offline foundation；
3. 单独建立 controlled runtime activation gate；
4. 使用非产品 sandbox fixture 验证写动作，再考虑真实产品任务；
5. 通用项目 onboarding 和 capability discovery；
6. Admin UI 管理 Provider、Model 和 Policy；
7. Monitoring、alerts、SLO、privacy/retention、backup/restore 和 DR；
8. Multi-tenant identity、quota、metering 和 commercial packaging；
9. 单独任务推进 production validation。
```
