# ORIS Session Wrap-up — 2026-04-06

更新时间：2026-04-06 12:21:06 UTC

## 1. 本轮已完成的核心事项

### 1.1 Feishu 真实生产入口
- 已完成 **Feishu direct webhook callback server** 切换与验证。
- 已解决 challenge code 校验、Basic Auth 误拦截、真实消息 ingress 单一事实源问题。
- 已确认 Feishu 实际消息能进入 ORIS 自建回调链路，而不是旧的双通道混跑路径。
- 已验证 meta 问题与普通问答路径的治理修正已经生效。

### 1.2 回答治理协议
- 已建立 **evidence-first answer protocol**。
- 核心要求：
  - 结论必须由数据支撑。
  - 必须说明数据是什么。
  - 必须说明出处名称。
  - 应尽量给出链接/报告名/公告名/API/日期等可定位信息。
  - 必须区分：事实 / 推断 / 假设 / 风险。
- 已写入：
  - `config/answer_policy.json`
  - `docs/ANSWER_PROTOCOL.md`
  - `docs/SOURCE_POLICY.md`
  - `docs/ROUTING_POLICY.md`

### 1.3 报告产物能力
- 已打通 **Word 正式报告 + Excel 辅助评分表** 输出能力。
- 已跑通 eval report 生成，产物已落盘到：
  - `outputs/evals/*.docx`
  - `outputs/evals/*.xlsx`
  - `outputs/evals/*.zip`
  - `outputs/evals/*.json`

### 1.4 Insight 存储底座
- 已安装 PostgreSQL。
- 已建立 `oris_insight` 数据库与 `insight` schema。
- 已落地 v1 数据模型，核心表包括：
  - `company`
  - `source`
  - `source_snapshot`
  - `evidence_item`
  - `metric_observation`
  - `analysis_run`
  - `report_artifact`
  - `delivery_task`
  - `watch_task`
  - `alert_event`
- 已写入：
  - `docs/INSIGHT_PLATFORM_ARCHITECTURE.md`
  - `docs/INSIGHT_DATA_MODEL.md`
  - `docs/INSIGHT_SKILL_ROADMAP.md`
  - `sql/insight_schema_v1.sql`

### 1.5 报告下载与分发安全
- 已完成从 `artifact_code` 直出链接，升级到 **delivery_code + expires + sig** 的 v2 模型。
- 已实现：
  - 下载签名
  - 过期时间
  - 最大下载次数
  - 下载审计
  - `used_count / last_downloaded_at / delivered_at`
- 已验证：
  - Control UI 仍受 Basic Auth 保护。
  - 公网签名下载链接可直接下载文件，不再被 Basic Auth 拦截。
  - 下载审计已能写入数据库并累计计数。
- 已写入：
  - `scripts/report_download_server.py`
  - `scripts/register_report_delivery.py`
  - `scripts/revoke_delivery_links.py`
  - `scripts/lib/report_delivery_runtime.py`
  - `sql/insight_schema_v2_download_security.sql`

---

## 2. 当前有效架构结论

### 2.1 当前对外问答主链路
- **Feishu → Nginx public route → ORIS direct callback server → ingress/bridge → model/tool routing → reply/send**

### 2.2 当前报告交付主链路
- **生成报告 → 注册 artifact → 生成 delivery_task → 为 Feishu/Qbot 生成签名下载链接 → 公网下载 → DB 审计**

### 2.3 当前状态判定
当前系统已经从“能否跑通”阶段，进入：
**AI 员工产品化 Phase 2：证据化回答 + 报告交付 + 洞察记忆底座阶段**

---

## 3. 当前仍需继续的事项

### 3.1 第一优先级
实现 **delivery executor**
- 扫描 `delivery_task.status='pending'`
- 真正把下载链接发到 Feishu / Qbot
- 回写：
  - `status=sent / failed`
  - `delivery_result_json`
  - `sent_at`
  - `error_message`

### 3.2 第二优先级
落地第一批 **insight skills scaffold**
建议先做 4 个：
- `company_profile_skill`
- `competitor_research_skill`
- `official_source_ingest_skill`
- `report_build_skill`

### 3.3 第三优先级
把 Insight DB 从“有表结构”升级到“持续沉淀数据”
包括：
- company/source/evidence/metric 的真实写入
- 周报/竞品跟踪/官网 diff/财报解读任务化
- 长期记忆与可审计研究闭环

---

## 4. 当前 authoritative docs（新对话优先读取）

1. `docs/PROJECT_STATE.md`
2. `memory/HANDOFF.md`
3. `docs/SESSION_WRAPUP_2026-04-06.md`
4. `docs/DOC_STATUS_MATRIX_2026-04-06.md`
5. `docs/ANSWER_PROTOCOL.md`
6. `docs/SOURCE_POLICY.md`
7. `docs/ROUTING_POLICY.md`
8. `docs/INSIGHT_PLATFORM_ARCHITECTURE.md`
9. `docs/INSIGHT_DATA_MODEL.md`
10. `docs/INSIGHT_SKILL_ROADMAP.md`
11. `docs/RUNBOOKS/INSIGHT_POSTGRES_BOOTSTRAP.md`
12. `docs/RUNBOOKS/REPORT_ARTIFACT_DELIVERY.md`
13. `docs/RUNBOOKS/REPORT_DOWNLOAD_SECURITY_V2.md`

---

## 5. 关键操作规范（新对话继续沿用）

- 全部用 **copy-paste 可执行命令**
- 不要让用户手工找文件或手工编辑文件
- Linux 命令中 **不要使用 `set -e`**
- 先验证，再 commit，再 push
- 优先把 GitHub 文档作为续航记忆，而不是依赖聊天短上下文
- 修改代码时，避免把配置重新写死成常量；优先走 config / DB / runtime policy
- 对外回答优先级：**正确性 > 稳定性 > 速度**
