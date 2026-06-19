# New Chat Bootstrap Prompt — 2026-06-19

继续 ORIS / OpenClaw / Codex-backed AI Dev Employee 商用化项目。

不要从头重新设计，不要依赖旧聊天上下文，不要脱离 GitHub 现有体系另起炉灶。必须先读取 GitHub 仓库 `ShanGouXueHui/oris` 中的持久化上下文。

GitHub Repo:

`https://github.com/ShanGouXueHui/oris`

请按顺序读取：

1. `memory/dev_employee/CONTEXT_INDEX.md`
2. `memory/dev_employee/CURRENT_STATE_2026-06-19.md`
3. `memory/dev_employee/SESSION_ARCHIVE_2026-06-19.md`
4. `memory/dev_employee/current_task.json`
5. `memory/dev_employee/current_task.md`
6. `docs/DEV_EMPLOYEE_OPENCLAW_READONLY_ENABLEMENT_DIAGNOSTIC_PLAN_2026-06-19.md`
7. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-19.md`
8. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
9. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
10. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`
11. `docs/DEV_EMPLOYEE_OPENCLAW_AGENT_END_POLICY_ADDENDUM_2026-06-18.md`
12. `docs/DEV_EMPLOYEE_OPENCLAW_PLUGIN_RUNTIME_HOOK_INSPECTION_ADDENDUM_2026-06-18.md`
13. `docs/DEV_EMPLOYEE_COMMERCIALIZATION_PRIORITY_2026-06-18.md`
14. `orchestration/project_registry.json`
15. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-19.md`
16. evidence commit `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

读取后先简要总结：

- 当前架构；
- 已完成能力；
- 当前插件、Skill 和工具策略状态；
- 当前任务进展；
- 最新失败的准确阶段；
- 当前商用化阻塞；
- 下一步最小安全动作；
- 后续商用优先级。

然后直接继续执行，不要重新规划整个系统。

## 当前不可逆产品决策

1. `https://control.orisfy.com` 的主界面是 OpenClaw 原生 UI 和原生会话体系。
2. 自研 ORIS Web Console 不再作为商用主界面，仅保留受限 `/admin` 和回滚/诊断路径。
3. 正式链路：

```text
用户
→ OpenClaw 原生 UI
→ 原生 ORIS Plugin / Agent Harness
→ ORIS 任务治理
→ Codex 真实代码执行
→ 产品提交、测试和 ORIS evidence 返回 OpenClaw
```

4. 不重新安装或升级 OpenClaw。
5. 复用现有 `openclaw-gateway.service` 和 `127.0.0.1:18789`。
6. 不恢复大范围 Prompt 关键词匹配创建任务。
7. ORIS 必须通过稳定 typed tools/actions/plugins 接入 OpenClaw。
8. Intake `127.0.0.1:18892` 和 enqueue/status `127.0.0.1:18891` 不得公网暴露。
9. 产品代码、测试和产品文档留在独立产品仓库。
10. `main` 是唯一主流分支。

## 当前插件与基线

- Plugin：`oris-dev-employee` `0.1.0`
- 安装结果：`INSTALLED_TOOLS_DENIED`
- Source commit：`8f174b49196aac90b505846200ce260f75355b41`
- Artifact SHA-256：`976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`
- Installation evidence：`b831470063bc640e498d2061fdaeb2bf8bc9639c`

Runtime-verified read-only tools：

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Runtime-verified typed hooks：

- `model_call_ended`
- `after_tool_call`
- `agent_end`

Readiness：

- 26/26 PASS
- evidence commit：`a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`

当前任务不允许增加写动作。

## 当前任务

- Task ID：`commercial-openclaw-readonly-tool-enable-20260618`
- Status：`blocked_after_dual_stage_policy_gateway_health_failure_rollback_complete`
- Current step：`diagnose_gateway_rejection_of_dual_stage_readonly_policy_before_retry`

目标：

仅启用三个批准的只读工具，完成直接调用、OpenClaw 原生自然语言调用和隐私安全 telemetry baseline。任一失败自动恢复 tools-denied 状态。

## 已完成调查

已验证：

- 三个工具直接调用成功；
- `oris-readonly-status` Skill 曾对 Agent `main` runtime-visible；
- 原生 Agent/Gateway transport 和持久会话工作；
- 早期三轮模型调用出现 `model_call_ended=3`、`agent_end=3`，但 `after_tool_call=0`；
- Skill 可见不等于工具物化，直接调用成功不等于模型获得工具；
- optional plugin tool materialization 和 active profile authorization 必须分阶段验证。

当前 source 已实现可回滚 dual-stage policy：

- `tools.allow`：物化 coding profile expansion 和批准工具；
- `tools.alsoAllow`：扩展 active profile；
- `tools.deny`：只移除三个批准工具；
- 其他配置不得变化；
- 失败恢复精确原配置。

相关 source commits：

- `741f24687c751ebfa405d8ea74c8a45a53a09161`
- `0182858e58fefdb267f7cb3cf8b76bf6a8064323`
- `c48a8741645cfd57ba24530a6dc4da767612568a`
- `d650a0f9e4686df4b46157ace680e9bb08e396ff`

## 最新执行结果

- RESULT：`FAILED`
- FAILURE：`RuntimeError:existing OpenClaw Gateway did not become healthy`
- Policy mode：`materialized-profile-plus-approved+created-profile-also-allow+skill-unrestricted`
- Candidate `tools.allow` count：13
- Candidate `tools.alsoAllow` count：3
- Rollback：healthy
- Product task submitted：NO
- Write tools added：NO
- Secrets printed：NO
- Evidence commit：`c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

失败发生在 candidate config 激活并重启现有 Gateway 后，Gateway 未通过健康检查。

因此本轮没有进入：

- runtime plugin inventory；
- direct tool calls；
- native Agent acceptance；
- telemetry acceptance；
- 最终 queue/product invariant 检查。

Evidence 中这些阶段的 false 表示 `NOT_CHECKED`，不是发现了写工具、队列变化或产品变化。

当前 runtime 按 healthy rollback 处理为 tools-denied baseline。

## 第一动作

不要立即重新执行 enablement，不要猜测下一种 policy 组合。

先严格执行：

1. 修改文件前，扫描目标工程文件是否已有重复定义、重复 parser、重复 policy、重复 profile expansion、重复 service helper；
2. 扫描硬编码：项目、路径、主机、端口、分支、provider、model、runtime version、验收项目特例；
3. 大文件先按 policy / runtime adapter / service control / validation / evidence / entrypoint 分层解耦；
4. 创建 GitHub-hosted diagnostic/remediation；
5. 在私有临时路径构建 candidate config；
6. 探测并运行已安装 OpenClaw 支持的 config/schema validation；
7. 验证 `tools.profile`、`tools.allow`、`tools.alsoAllow`、group selectors、optional plugin tools 在 `2026.5.19` 中的实际兼容性；
8. 记录变更前 Gateway PID/health；
9. 如果受控重启失败，在 rollback 前捕获脱敏、限长的 `systemctl status` 和 `journalctl` 证据；
10. evidence 使用 `PASS` / `FAIL` / `NOT_CHECKED`，禁止用 false 混淆未执行；
11. 恢复精确 tools-denied 配置并验证 Gateway 健康；
12. detached worktree 提交脱敏 evidence；
13. 读取 evidence 后再选择最小 runtime-accepted policy，不能盲目重试。

## 环境

- ORIS 开发/控制/执行机：`43.106.55.255`，用户 `admin`
- ORIS 路径：`/home/admin/projects/oris`
- 产品路径：`/home/admin/projects/oris-final-acceptance-api`
- 产品完成 commit/remote main：`bcb93e17ea88704548101f5e4a5c460e15a80ec7`
- OpenClaw：`127.0.0.1:18789`
- enqueue/status：`127.0.0.1:18891`
- Intake：`127.0.0.1:18892`
- Web Console：`127.0.0.1:18893`
- Bridge：`oris-dev-employee-bridge.service`
- 杭州生产机：`8.136.28.6`，用户 `deploy`，不要触碰
- OpenClaw：`2026.5.19 (a185ca2)`
- Node：`v22.22.2`
- npm：`10.9.7`
- Codex CLI：真实代码执行器
- PostgreSQL：`oris_insight` / schema `insight`，与 Dev Employee task state 分离
- Database security：`ALREADY_SECURE_AND_VERIFIED`
- Latest DB evidence：`bc799a640138a19800270ecab1a656f09d70252a`
- Provider/model 是 runtime fact，不允许在通用代码硬编码
- ZenMux 排除，除非用户明确重新开放

## 固定工程与交互方式

- 使用中文，职业化、直接、结构化；
- 不要让我决定日常工程细节；
- 长脚本、文档和补丁直接写入 GitHub；
- 需要服务器执行时，只给一条短命令运行 GitHub 中的 `.sh`；
- 不要给长 heredoc；
- 日志写入 `logs/dev_employee/` 并提交脱敏 evidence；
- 直接从 GitHub 查看日志，不让我粘贴长输出；
- 每个执行脚本最后只输出一个 `===== SUMMARY =====`；
- Summary、GitHub 和聊天不得输出 Token、密码、密钥、raw config 或 private marker 原文；
- Linux 用户脚本不要使用 `set -e`；
- 修改文件前必须扫描重复定义和硬编码；
- 一个规则只有一个权威来源；
- 大文件必须分层解耦；
- 配置与代码分离；
- 允许备份和 detached worktree，但不创建竞争性长期分支；
- 构建通用商用版本，不为验收项目硬编码特例；
- 完成必须验证明确交付物、真实测试、commit SHA、remote SHA 和 GitHub evidence；
- 不要在 commit 后继续追加同一个 tracked log。

## 后续商用优先级

1. 解决 Gateway 对 candidate read-only policy 的拒绝；
2. 完成三个只读工具的原生自然语言验收；
3. 建立真实、隐私安全的 model/tool/agent latency baseline；
4. P0 完成后再设计带 approval、RBAC、idempotency、audit 的 typed write actions；
5. 通用项目 onboarding 和 capability discovery；
6. Admin UI 管理 provider/model/policy；
7. monitoring、privacy/retention、backup/restore、DR；
8. multi-tenant identity、quota、metering、commercial packaging。
