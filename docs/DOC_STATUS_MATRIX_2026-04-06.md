# ORIS Document Status Matrix — 2026-04-06

## A. 当前应优先依赖的文档（Authoritative）

| 文档 | 状态 | 说明 |
|---|---|---|
| `docs/PROJECT_STATE.md` | current | 当前系统状态总入口 |
| `memory/HANDOFF.md` | current | 新对话续航入口 |
| `docs/SESSION_WRAPUP_2026-04-06.md` | current | 本轮阶段总结 |
| `docs/ANSWER_PROTOCOL.md` | current | 证据优先回答协议 |
| `docs/SOURCE_POLICY.md` | current | 数据来源与出处规则 |
| `docs/ROUTING_POLICY.md` | current | 路由治理原则 |
| `docs/INSIGHT_PLATFORM_ARCHITECTURE.md` | current | 洞察平台架构 |
| `docs/INSIGHT_DATA_MODEL.md` | current | 洞察数据模型 |
| `docs/INSIGHT_SKILL_ROADMAP.md` | current | skill 路线图 |
| `docs/RUNBOOKS/INSIGHT_POSTGRES_BOOTSTRAP.md` | current | PG 启动/排障基线 |
| `docs/RUNBOOKS/REPORT_ARTIFACT_DELIVERY.md` | current | 报告注册与投递链路 |
| `docs/RUNBOOKS/REPORT_DOWNLOAD_SECURITY_V2.md` | current | 下载安全 v2 运行基线 |

## B. 保留但应按“历史阶段文档”阅读（Historical）

| 文档 | 状态 | 说明 |
|---|---|---|
| `docs/DECISIONS/2026-04-06-feishu-final-webhook-cutover.md` | historical | 记录切换动作，现已完成 |
| `docs/DECISIONS/2026-04-06-feishu-webhook-verified.md` | historical | 记录 challenge/verification 成功 |
| `docs/DECISIONS/2026-04-06-feishu-single-source-of-truth.md` | historical-but-relevant | ingress 单一事实源原则仍有效 |
| `docs/DECISIONS/2026-04-06-ability-first-routing-principle.md` | historical-but-relevant | 能力优先路由原则仍有效 |
| `docs/DECISIONS/2026-04-06-feishu-exact-reply-and-brokenpipe-fix.md` | historical | 偏调试/修复记录 |
| `docs/DECISIONS/2026-04-06-postgres-insight-bootstrap.md` | historical | PG 初始化阶段记录 |
| `docs/DECISIONS/2026-04-06-report-artifact-registry-and-delivery-queue.md` | historical-but-relevant | artifact/delivery 队列奠基文档 |
| `docs/DECISIONS/2026-04-06-insight-storage-compat-fix.md` | historical-but-relevant | insight storage 兼容层修正 |

## C. 已被更高版本结论覆盖（Superseded）

| 文档 | 状态 | 被谁覆盖 |
|---|---|---|
| `docs/DECISIONS/2026-04-06-report-download-public-route.md` | superseded | 被 `report-download-security-v2` 覆盖 |
| `docs/DECISIONS/2026-04-06-report-download-channel.md` | superseded | 被 `REPORT_ARTIFACT_DELIVERY.md` + `REPORT_DOWNLOAD_SECURITY_V2.md` 覆盖 |
| `docs/DECISIONS/2026-04-06-download-rewrite-fix.md` | superseded | 被当前 `report_download_server.py` 与 v2 runbook 覆盖 |
| `docs/DECISIONS/2026-04-06-signed-download-auth-model.md` | superseded | 被 delivery-code security v2 覆盖 |

## D. 阅读建议

新对话中，优先顺序如下：

1. `docs/PROJECT_STATE.md`
2. `memory/HANDOFF.md`
3. `docs/SESSION_WRAPUP_2026-04-06.md`
4. 上述 Authoritative 文档
5. 需要追溯时再看 Historical / Superseded 文档
