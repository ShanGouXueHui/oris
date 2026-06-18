# New Chat Bootstrap Prompt — 2026-06-18

继续 ORIS / OpenClaw / Codex-backed AI Dev Employee 商用化项目。

不要从头重新设计，不要依赖旧聊天上下文，不要脱离 GitHub 现有体系另起炉灶。必须先读取 GitHub 仓库 `ShanGouXueHui/oris` 中的持久化上下文。

GitHub Repo:

`https://github.com/ShanGouXueHui/oris`

请按顺序读取：

1. `memory/dev_employee/CONTEXT_INDEX.md`
2. `memory/dev_employee/CURRENT_STATE_2026-06-18.md`
3. `memory/dev_employee/SESSION_ARCHIVE_2026-06-18.md`
4. `memory/dev_employee/OPENCLAW_NATIVE_PLUGIN_INSTALL_COMPLETION_2026-06-18.md`
5. `memory/dev_employee/current_task.json`
6. `memory/dev_employee/current_task.md`
7. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-18.md`
8. `docs/DEV_EMPLOYEE_OPENCLAW_AGENT_END_POLICY_ADDENDUM_2026-06-18.md`
9. `docs/DEV_EMPLOYEE_OPENCLAW_PLUGIN_RUNTIME_HOOK_INSPECTION_ADDENDUM_2026-06-18.md`
10. `docs/DEV_EMPLOYEE_COMMERCIALIZATION_PRIORITY_2026-06-18.md`
11. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
12. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
13. `orchestration/project_registry.json`
14. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-18.md`

读取完成后先简要总结：

- 当前架构；
- 已完成能力；
- 当前插件安装与策略状态；
- 当前商用化阻塞；
- 当前任务；
- 下一步最小安全动作；
- 后续商用优先级。

然后直接继续执行，不要重新规划整个系统。

## 不可逆产品决策

1. `https://control.orisfy.com` 的主界面是 OpenClaw 原生 UI 和原生会话体系。
2. 自研 ORIS Web Console 不再作为商用主界面，仅保留受限 `/admin` 和回滚/诊断路径。
3. 正式链路为：

   `用户 -> OpenClaw 原生 UI -> 原生 ORIS Plugin / Agent Harness -> ORIS 任务治理 -> Codex 真实代码执行 -> 产品提交、测试和 ORIS evidence 返回 OpenClaw`

4. 不重新安装或升级 OpenClaw。
5. 复用现有 `openclaw-gateway.service` 和 `127.0.0.1:18789`。
6. 不恢复大范围 Prompt 关键词匹配创建任务。
7. ORIS 通过稳定 typed tools/actions/plugins 接入 OpenClaw。
8. Intake `127.0.0.1:18892` 和 enqueue/status `127.0.0.1:18891` 不得公网暴露。
9. 产品代码、测试和产品文档留在独立产品仓库；ORIS 只放平台编排、策略和 evidence。
10. `main` 是唯一主流分支。

## 当前插件状态

插件：`oris-dev-employee` `0.1.0`

安装结果：`INSTALLED_TOOLS_DENIED`

Source commit：`8f174b49196aac90b505846200ce260f75355b41`

Artifact SHA-256：`976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`

Evidence commit：`b831470063bc640e498d2061fdaeb2bf8bc9639c`

已注册并 runtime-verified 的只读工具：

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

已注册并 runtime-verified 的 typed hooks：

- `model_call_ended`
- `after_tool_call`
- `agent_end`

当前策略：

- 插件已启用；
- plugin error count = 0；
- 三个工具仍在 `tools.deny`，尚未暴露给模型；
- `tools.allow` 在安装时保持不变；
- 仅 `oris-dev-employee` 设置 `allowConversationAccess=true`，用于注册 `agent_end`；
- 没有 submit/cancel/retry 写工具；
- Gateway 认证仍为 token，安装未改变认证凭据；
- 不要重新安装插件。

## 当前任务

Task ID：`commercial-openclaw-readonly-tool-enable-20260618`

Status：`plugin_installed_tools_denied_pending_controlled_enable`

Current step：`read_only_readiness_before_readonly_tool_enable`

目标：仅启用三个已批准的只读工具，完成直接调用与 OpenClaw 原生浏览器验收，并建立真实延迟和隐私安全 telemetry baseline。当前任务不允许增加任何写动作。

## 第一步必须执行

不要立即修改 `openclaw.json`，不要立即启用工具。

先在 GitHub 创建并运行一个只读 readiness 脚本，检查：

1. 私有 install marker 和 pre-install backup 的存在、权限、JSON 合法性和关联关系，不输出任何值；
2. plugin cold/runtime inventory；
3. 三个工具和三个 hooks 的精确匹配；
4. 当前 `tools.deny` 是否包含三个工具；
5. 当前有效 `tools.allow`、tool profile 和 agent-specific policy，确定启用所需的最小配置变更；
6. scoped `allowConversationAccess=true` 是否仅对 ORIS plugin 生效；
7. Gateway、public root、`/admin`、`/_oris-chat-shell` 状态；
8. 18891 和 18892 是否仍 loopback-only；
9. telemetry 文件路径、权限、rotation 状态、字段 schema 和内容安全扫描；
10. active queue count、queue fingerprint；
11. 产品仓库 HEAD、remote main、clean worktree baseline；
12. 不存在写工具、不提交产品任务；
13. OpenClaw 配置和服务 PID 在只读检查前后不变。

只读脚本必须：

- 不修改配置；
- 不 reload/restart；
- 不启用工具；
- 不提交产品任务；
- 不打印 Token、密码、密钥、marker 原文或配置原文；
- 日志写入 `logs/dev_employee/`；
- 通过 detached worktree 提交脱敏 evidence；
- 最后输出 `===== SUMMARY =====`。

读取 evidence 后，再创建可回滚 enablement 脚本：

- 只删除/调整三个已批准工具所需的有效 deny/allow 规则；
- 保持所有写工具不存在；
- 备份配置并验证 JSON；
- 只重启现有 Gateway；
- 直接调用三个只读工具；
- 浏览器中用自然语言验证 queue/latest/task status，不要求 ORIS 特殊命令语法；
- 验证没有任务提交、queue fingerprint 不变、产品仓库不变；
- 验证 telemetry 出现 `model_call_ended`、`after_tool_call`、`agent_end`，且不包含对话内容或秘密；
- 获取可用的 TTFT、model duration、tool duration 和 total agent duration；
- 任一失败自动恢复为 tools-denied 状态。

## 环境

- ORIS 服务器：`43.106.55.255`
- 用户：`admin`
- ORIS 路径：`/home/admin/projects/oris`
- 产品路径：`/home/admin/projects/oris-final-acceptance-api`
- 产品完成 commit/remote main：`bcb93e17ea88704548101f5e4a5c460e15a80ec7`
- OpenClaw：`127.0.0.1:18789`
- enqueue/status：`127.0.0.1:18891`
- Intake：`127.0.0.1:18892`
- Web Console：`127.0.0.1:18893`
- Bridge：`oris-dev-employee-bridge.service`
- 杭州生产机：`8.136.28.6`，用户 `deploy`；除非明确生产任务，不要触碰
- OpenClaw：`2026.5.19 (a185ca2)`
- Node：`v22.22.2`
- npm：`10.9.7`
- Codex CLI：真实代码执行器

## 固定工程与交互方式

- 使用中文，职业化、直接、结构化；
- 不要让我决定日常工程细节；
- 长脚本、文档和补丁直接写入 GitHub；
- 给我一条短命令运行 GitHub 中的 `.sh`；
- 不要给长 heredoc，终端命令可能被截断；
- 日志写入 `logs/dev_employee/` 并提交脱敏 evidence；
- 直接从 GitHub 查看日志，不让我粘贴长输出；
- 每个执行脚本最后必须输出 `===== SUMMARY =====`；
- SUMMARY、GitHub 和聊天中不得输出 Token、密码或密钥；
- Linux 用户脚本不要使用 `set -e`；
- 允许备份，但不创建竞争性长期分支；
- 坚持分层解耦、配置分离、一个规则一个权威来源；
- 构建通用商用版本，不为验收项目硬编码特例；
- 完成必须验证所有明确交付物、真实测试、commit SHA、remote SHA 和 GitHub evidence；
- 不要在 commit 后继续追加同一个 tracked log；
- 必要时使用 detached worktree 提交 evidence。
