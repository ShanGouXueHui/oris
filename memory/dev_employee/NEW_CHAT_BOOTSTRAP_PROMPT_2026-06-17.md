# ORIS / OpenClaw / Codex-backed AI Dev Employee — New Chat Bootstrap Prompt

继续 ORIS / OpenClaw / Codex-backed AI Dev Employee 商用化项目。

不要从头重新设计，不要依赖旧聊天上下文，不要脱离 GitHub 现有体系另起炉灶。必须先读取 GitHub 仓库 `ShanGouXueHui/oris` 中的持久化上下文。

GitHub Repo:

`https://github.com/ShanGouXueHui/oris`

请按顺序读取：

1. `memory/dev_employee/CONTEXT_INDEX.md`
2. `memory/dev_employee/CURRENT_STATE_2026-06-17.md`
3. `memory/dev_employee/current_task.json`
4. `memory/dev_employee/current_task.md`
5. `docs/DEV_EMPLOYEE_NATIVE_OPENCLAW_UI_DECISION_2026-06-17.md`
6. `docs/DEV_EMPLOYEE_NATIVE_OPENCLAW_UI_MIGRATION_PLAN_2026-06-17.md`
7. `docs/DEV_EMPLOYEE_ENVIRONMENT_ADDENDUM_2026-06-17.md`
8. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
9. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
10. `docs/DEV_EMPLOYEE_QUEUE_LIFECYCLE_HARDENING_2026-06-16.md`
11. `memory/dev_employee/FINAL_ACCEPTANCE_COMPLETION_2026-06-16.md`
12. `orchestration/project_registry.json`
13. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-17.md`

读取完成后，先简要总结：

- 当前架构；
- 已完成能力；
- 当前商用化阻塞；
- 当前任务；
- 下一步最小安全动作；
- 后续商用优先级。

然后直接继续执行，不要重新规划整个系统。

## 当前不可逆转的产品决策

当前 `https://control.orisfy.com` 展示的 `ORIS AI 开发员工` 页面是 ORIS 仓库中自研的 Web Console v5，不是 OpenClaw 原生界面。

该自研界面不再作为商用主界面，原因包括：

- 没有新建对话；
- 没有历史会话列表；
- 没有切换、清空、归档；
- 一个长期 Cookie 复用同一个服务端会话；
- 历史失败信息混在同一对话；
- 自定义意图和关键词路由改变正常 Prompt 语义；
- 用户需要适应 ORIS 特定规则。

正式方向：

```text
用户
→ OpenClaw 原生 UI 和原生会话体系
→ Agent Harness 工具/策略适配层
→ ORIS 任务治理
→ Codex 真实代码执行
→ 产品提交、测试和 ORIS evidence 返回 OpenClaw
```

要求：

- 不重新安装或升级 OpenClaw；
- 复用现有 `openclaw-gateway.service`；
- Harness 仅作为后端工具、策略、结构化输出和回退层；
- ORIS 通过稳定 tools/actions/plugins 接入 OpenClaw；
- 不再依靠大范围 Prompt 关键词匹配创建任务；
- 自研 Web Console 仅临时保留为受限诊断/回滚页面；
- `/admin` 继续受限保留。

## 当前任务

Task ID:

`commercial-native-openclaw-ui-20260617`

当前步骤：

`restore_native_openclaw_ui_as_primary_public_experience`

不要立即修改 Nginx，也不要提交新的产品任务。

第一步必须做只读发现，生成 GitHub 托管的 `.sh`，检查：

1. OpenClaw systemd unit、进程、监听端口和配置键；
2. 原生 UI 根路径、静态资源和 SPA 行为；
3. WebSocket 路径、Upgrade Header 和超时要求；
4. Token/设备配对/认证方式，但不得输出值；
5. 当前安装版本是否支持新建对话、历史、切换、清空/归档；
6. `nginx -T` 的真实加载顺序；
7. 实际生效的 `control.orisfy.com` HTTP/HTTPS server block；
8. 当前 `/`、`/admin`、OpenClaw 代理路径；
9. 是否存在重复或被忽略的 Nginx 配置；
10. 服务状态、活跃队列和产品仓库 baseline。

该脚本必须：

- 只读；
- 不 reload/restart；
- 不提交产品任务；
- 不打印秘密；
- 将详细日志写入 `logs/dev_employee/` 并提交 GitHub；
- 最后输出 `===== SUMMARY =====`。

读取发现 evidence 后，再设计并执行可回滚迁移：

- `/` → OpenClaw 原生 UI `127.0.0.1:18789`；
- OpenClaw WebSocket/静态/API 路由 → `18789`；
- `/admin` → ORIS Web Console `127.0.0.1:18893`；
- 非默认受限回滚路径 → 自研 ORIS chat shell；
- intake `127.0.0.1:18892` 不得公网暴露。

## 已完成能力

已经通过：

- 真实公网 Web → intake → queue → bridge → Codex → 产品测试/commit/push → remote SHA → ORIS evidence 的全链路验收；
- Codex admin 登录、non-interactive exec 和 systemd bridge 同认证上下文；
- Codex auth preflight；
- terminal states 和失败后停止轮询；
- transaction-safe queue kernel；
- lease、heartbeat、timeout、cancel、rollback、retry、concurrency；
- intake v2、bridge v3；
- OpenClaw runtime discovery 和 provider probe；
- Agent Harness 后端集成；
- 公网 chat POST 的 Nginx 精确放行，其他写接口继续阻断；
- `状态码` 被误判为状态查询的问题已修复；
- `不要修改任何密钥` 被误判为密钥操作的问题已修复。

## 当前受控产品任务结果

Task ID:

`chat-oris-final-acceptance-api-20260617-051313-c802347ff17c`

Product commit:

`927f1968cc86bfd5213670f4eaa171fc1a3be620`

已完成：

- `GET /capabilities`；
- `service`、`storage`、`features`；
- `features` 包含 `task_crud`、`filtering`、`stats`；
- pytest 覆盖。

未完成：

- 用户要求的 README API 列表更新。

因此该任务只能视为部分完成。OpenClaw 原生 UI 验收通过后，再补 README，运行检查，commit/push，验证产品 remote SHA 和 ORIS evidence。

## 环境

- ORIS 服务器：`43.106.55.255`
- 用户：`admin`
- ORIS 路径：`/home/admin/projects/oris`
- 产品路径：`/home/admin/projects/oris-final-acceptance-api`
- 公网入口：`https://control.orisfy.com`
- OpenClaw：`127.0.0.1:18789`，`openclaw-gateway.service`
- Web Console：`127.0.0.1:18893`，`oris-dev-employee-web-console.service`
- Intake：`127.0.0.1:18892`，`oris-dev-employee-intake.service`
- Bridge：`oris-dev-employee-bridge.service`
- 杭州生产机：`8.136.28.6`，用户 `deploy`；除非明确任务要求，不要触碰。

## 固定交互方式

- 使用中文，职业化、直接、结构化；
- 不要让我决定日常工程细节；
- 长脚本、文档和补丁直接写入 GitHub；
- 给我一条短命令运行 GitHub 中的 `.sh`；
- 不要给长 heredoc，终端命令可能被截断；
- 日志写入 `logs/dev_employee/` 并提交 GitHub；
- 你直接从 GitHub 查看日志，不让我粘贴长输出；
- 每个执行脚本最后必须输出 `===== SUMMARY =====`；
- SUMMARY、GitHub 和聊天中不得输出 Token、密码、密钥；
- Linux 用户脚本不要使用 `set -e`；
- `main` 是唯一主流分支；
- 允许备份，但不创建竞争性长期分支；
- ORIS 只放平台编排和 evidence，产品代码留在独立产品仓库；
- 坚持分层解耦、配置分离、一个规则一个权威来源；
- 构建通用商用版本，不为验收项目硬编码特例；
- 完成必须有真实测试、所有明确交付物、commit SHA、remote SHA 和 GitHub evidence；
- 不要在 commit 后继续追加同一个 tracked log；必要时使用 detached worktree 提交 evidence。
