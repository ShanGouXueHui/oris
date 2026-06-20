# Final Seamless Bootstrap Prompt — 2026-06-20

Copy the text below into a new conversation.

```text
继续 ORIS / OpenClaw / Codex-backed AI Dev Employee 商用化项目。

不要从头重新设计，不要依赖旧聊天上下文，不要脱离 GitHub 现有体系另起炉灶。必须先读取 GitHub 仓库 `ShanGouXueHui/oris` 的持久化上下文。

GitHub Repo：
https://github.com/ShanGouXueHui/oris

请按顺序读取：

1. `memory/dev_employee/CONTEXT_INDEX_ADDENDUM_2026-06-20.md`
2. `memory/dev_employee/CONTEXT_INDEX.md`
3. `memory/dev_employee/CURRENT_STATE_2026-06-20.md`
4. `memory/dev_employee/SESSION_ARCHIVE_2026-06-20.md`
5. `memory/dev_employee/ENVIRONMENT_AND_WORKING_CONTEXT_2026-06-20.md`
6. `memory/dev_employee/current_task.json`
7. `memory/dev_employee/current_task.md`
8. `docs/DEV_EMPLOYEE_CODE_FIRST_CONTINUATION_GATE_2026-06-20.md`
9. `docs/DEV_EMPLOYEE_EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_PLAN_2026-06-20.md`
10. evidence commit `d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`
11. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_CORRECTION_2026-06-20.md`
12. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-19.md`
13. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
14. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
15. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`
16. `orchestration/project_registry.json`

读取后先简要总结：

- 当前架构；
- 已完成能力；
- Plugin、Skill、typed tools、hooks 状态；
- 当前 runtime 和 rollback 状态；
- 最新失败的准确阶段；
- 当前商用阻塞；
- 原始任务中尚未完成的事项；
- 下一步最小安全动作；
- 后续商用优先级。

然后直接继续执行，不要重新设计整个系统。

第一优先级：先修正代码问题，再推进功能。

必须先对当前 `main` 做完整 code-first audit，覆盖当前全部新增的 effective-surface diagnostic 文件和调用链，重点检查并修复：

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

不要通过 scanner allowlist 隐藏真实问题。一个规则只保留一个权威实现。大文件必须按 policy、runtime adapter、service control、validation、evidence、entrypoint 分层解耦。

在得到以下结果前，禁止访问 OpenClaw runtime、禁止重启 Gateway、禁止运行 `tools.effective`、禁止模型调用、禁止调用 ORIS tool、禁止提交产品任务：

RESULT=CODE_AUDIT_PASS
DUPLICATE_BINDINGS=0
AUTHORITY_VIOLATIONS=0
DUPLICATE_FUNCTION_BODIES=0
IMPORT_CYCLES=0
OVERSIZED_MODULES=0
FORBIDDEN_HARDCODING=0
LEGACY_PATH_FINDINGS=0
CONTRACT_ERROR=
OPENCLAW_ACCESSED=NO
GATEWAY_RESTARTED=NO
TASK_SUBMITTED=NO

代码门通过后，再执行一次：

`scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh`

该诊断必须：

- 使用 native Gateway RPC `tools.effective`；
- 使用 persisted Agent session context；
- 不运行 model turn；
- 不调用 ORIS tool；
- 不提交产品任务；
- 不增加 write tool；
- 只记录脱敏的 approved-tool presence/count/ownership；
- 不记录 raw RPC、无关工具名、tool description、session 原文、prompt、conversation content、tool args/results、secret 或 raw config；
- 无论成功失败都恢复 exact tools-denied config、marker、Skill state；
- 验证 Gateway、queue、product、listener 最终不变量；
- 使用 detached worktree 提交 evidence。

读取 GitHub evidence 后再决策：

- 三个 ORIS 工具不在 effective surface：修复 OpenClaw optional-tool materialization/session-policy；
- 三个工具在 effective surface：诊断 provider/model tool-call capability 和 Agent Harness routing，不得硬编码 provider/model；
- RPC 不可用或不安全：停止并修复 diagnostic path，不得以 direct invocation、plugin catalog 或 prompt inference 代替。

禁止再次运行 `scripts/dev_employee_enable_openclaw_readonly_tools.sh`，直到 effective-surface 边界解决并在 GitHub 中形成新的受控授权。

当前不可逆产品决策：

1. `https://control.orisfy.com` 主界面是 OpenClaw 原生 UI 和原生会话体系；
2. 自研 ORIS Web Console 仅保留受限 `/admin` 和回滚/诊断路径；
3. 正式链路：用户 → OpenClaw 原生 UI → 原生 ORIS Plugin / Agent Harness → ORIS 任务治理 → Codex 真实代码执行 → 产品提交、测试和 ORIS evidence 返回 OpenClaw；
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
- enqueue/status：`127.0.0.1:18891`；
- Intake：`127.0.0.1:18892`；
- Web Console：`127.0.0.1:18893`；
- PostgreSQL：`oris_insight` / schema `insight`，仅用于 research/insight，与 Dev Employee task state 分离；
- Provider/Model 是 runtime fact，不允许在通用代码中硬编码。

交互和工程方式：

- 使用中文，职业化、直接、结构化；
- 不要让我决定日常工程细节；
- 长脚本、文档和补丁直接写入 GitHub；
- 需要服务器执行时只给一条短命令运行 GitHub 中的脚本；
- 不要给长 heredoc；
- 详细日志写入 `logs/dev_employee/` 并从 GitHub 查询；
- 每个执行脚本最后只输出一个 `===== SUMMARY =====`；
- GitHub、Summary 和聊天不得输出敏感配置、认证信息、会话原文、conversation content 或 private marker；
- Linux 用户脚本不要使用 `set -e`；
- 配置与代码分离；
- 可以备份和使用 detached worktree，但不创建竞争性长期分支；
- 构建通用商用版本，不为验收项目硬编码特例；
- 完成必须验证真实交付物、测试、commit SHA、remote SHA 和 GitHub evidence；
- 不要在 commit 后继续追加同一个 tracked log。

后续商用优先级：

1. 当前 `main` 代码治理全部归零；
2. 解决 effective tool materialization 或 provider/model tool-call capability；
3. 完成三个只读工具的原生自然语言验收；
4. 建立真实、隐私安全的 model/tool/agent latency baseline；
5. P0 后设计带 approval、RBAC、project authorization、idempotency、audit 的 typed write actions；
6. 通用项目 onboarding 和 capability discovery；
7. Admin UI 管理 Provider、Model 和 Policy；
8. Monitoring、privacy/retention、backup/restore 和 DR；
9. Multi-tenant identity、quota、metering 和 commercial packaging。
```
