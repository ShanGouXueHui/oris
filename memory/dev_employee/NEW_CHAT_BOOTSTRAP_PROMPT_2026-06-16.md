# ORIS Dev Employee — New Chat Bootstrap Prompt

Copy the content below into a new ChatGPT conversation.

---

继续 ORIS / OpenClaw / Codex-backed AI Dev Employee 商用化项目。

不要从头重新设计，不要脱离 GitHub 现有体系另起炉灶。先读取 GitHub 仓库 `ShanGouXueHui/oris` 中的权威持久化上下文，再继续执行。

## 一、必读顺序

按顺序读取：

1. `memory/dev_employee/CONTEXT_INDEX.md`
2. `memory/dev_employee/CURRENT_STATE_2026-06-16.md`
3. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-16.md`
4. `memory/dev_employee/current_task.json`
5. `memory/dev_employee/current_task.md`
6. `docs/DEV_EMPLOYEE_COMMERCIAL_ARCHITECTURE_2026-06-16.md`
7. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_2026-06-16.md`
8. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
9. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`
10. `orchestration/project_registry.json`
11. `logs/dev_employee/goal-oris-final-acceptance-api-20260616-031022.codex.log`
12. `logs/dev_employee/codex_failed_diagnostics/goal-oris-final-acceptance-api-20260616-031022-20260616031848.log`

读取后，先用简洁结构总结：

- 当前架构状态；
- 已完成能力；
- 当前阻塞点；
- 下一步最小安全动作；
- 商用化后续优先级。

然后直接继续执行，不要停留在重新规划。

## 二、当前任务

当前失败任务：

- Task ID：`goal-oris-final-acceptance-api-20260616-031022`
- Project：`oris-final-acceptance-api`
- Status：`codex_failed`
- Root cause：`codex_authentication`
- Diagnostic commit：`6fbc0ba1636ca01865b9565e68fdf6689ed6cae5`
- ORIS failure evidence commit：`ea2089c5344c67e016601de8993ef365591daa06`

任务目标原本是：

- 在 `ShanGouXueHui/oris-final-acceptance-api` 新增 `GET /readonly-e2e`；
- 返回严格等于 `{"readonly_e2e": true}`；
- 增加 pytest；
- 测试通过后 commit、push；
- ORIS 写入完整 GitHub evidence。

公网 Web 提交、intake、queue、bridge claim 均已成功。失败发生在 Codex 执行前的认证阶段，产品代码没有变更，也没有产品 commit。

## 三、下一步必须先做

不要立即重新提交真实项目任务。

先完成：

1. 从 GitHub 读取 Codex 失败日志；
2. 设计并直接上传 GitHub 脚本，用于安全修复/验证 Codex 登录；
3. 验证 Linux 用户 `admin` 下无副作用的 non-interactive `codex exec`；
4. 验证 `oris-dev-employee-bridge.service` 使用相同 HOME/auth 上下文；
5. 在 bridge 增加 Codex auth preflight；
6. 将 `codex_failed` 等失败状态纳入 terminal states，停止无意义轮询；
7. 修复后使用新 Task ID 从公网 Web UI 重跑同一目标；
8. 核验 product commit、remote SHA、pytest、ORIS evidence 和最终 completed 状态。

## 四、环境

- ORIS 开发/执行服务器：`43.106.55.255`
- 用户：`admin`
- ORIS 本地路径：`/home/admin/projects/oris`
- 产品本地路径：`/home/admin/projects/oris-final-acceptance-api`
- ORIS GitHub：`https://github.com/ShanGouXueHui/oris`
- 产品 GitHub：`https://github.com/ShanGouXueHui/oris-final-acceptance-api`
- 正式域名：`orisfy.com`
- 公网入口：`https://control.orisfy.com`
- Web Console：`127.0.0.1:18893`
- Intake：`127.0.0.1:18892`
- Bridge：`oris-dev-employee-bridge.service`
- 另有杭州生产机：`8.136.28.6`，用户 `deploy`；除非任务明确要求，不要触碰。

## 五、固定交互方式

1. 使用中文，职业化、直接、结构化。
2. 不要让用户决定日常工程细节；你应基于证据选择下一步。
3. 长脚本、文档、补丁直接修改/上传 GitHub，不要在聊天里打印大段内容。
4. 用户执行方式：从 GitHub 拉取后运行 `.sh` 文件，尽量一条短命令。
5. 日志写入 `logs/dev_employee/` 并自动 commit/push；你从 GitHub 查看。
6. 不要让用户粘贴长日志。
7. 每个用户执行脚本末尾必须输出：

```text
===== SUMMARY =====
...
SEND_TO_CHAT=THIS_SUMMARY_ONLY
===== END SUMMARY =====
```

8. 用户只会把 SUMMARY 发回来。
9. SUMMARY、GitHub 日志、聊天均不得输出 Token、密码、密钥、认证文件内容。
10. Linux 用户脚本不要使用 `set -e`。
11. 命令和脚本要可重复执行、可备份、可回滚、先检查后 reload/restart。

## 六、工程规范

- 分层解耦：Access / Security / Task Kernel / Planning / Execution / Validation / Evidence / Evaluation。
- 配置分离：Secrets 本地保存；稳定非敏感配置进仓库；运行噪音不提交；高频策略进 DB/Admin UI。
- ORIS 仓库只放平台编排和 evidence；产品代码必须在独立产品仓库。
- `main` 是唯一主流分支；允许备份，不创建竞争性长期分支。
- 一个规则只有一个权威来源。
- 构建通用商用版本，不要把 `oris-final-acceptance-api` 特例硬编码到共享架构。
- 完成必须有真实测试、commit SHA、remote SHA 和 GitHub evidence，不接受模型口头宣称。
- Intake 18892 继续保持非公网。
- 公网提交继续保留 HTTPS + Basic Auth + Console Token + Project Allowlist + Audit。

## 七、商用化方向

当前 P0：恢复 Codex 执行可靠性并完成真实 E2E。

随后推进：

- canonical task state machine；
- executor/provider/auth preflight；
- terminal state、retry、timeout、cancel、concurrency；
- registry-driven 多项目接入；
- RBAC/项目级授权；
- 事务型任务/event store；
- observability、alerts、audit retention；
- 安装、升级、备份、回滚、灾备 runbook；
- 去除一次性 patch 脚本堆积，收敛到正式模块和安装器；
- 通用商用 API 与 UI。

开始时先读取 GitHub，不要让我重新解释历史。

---
