# Decision: ORIS Insight 主库存储初始化为 PostgreSQL

## 日期
2026-04-06

## 决策
ORIS 企业竞争力洞察主库存储正式采用 PostgreSQL。
- database: oris_insight
- schema: insight
- app user: oris_app

## 原因
1. 证据链、引用链、artifact 元数据、监控任务适合关系型建模
2. PostgreSQL 对 JSONB、索引、审计型查询更友好
3. 与 ORIS “证据优先、可审计、可追溯”方向一致
4. 后续接 Word / Excel artifact、Feishu / Qbot 下载分发更顺

## 本次已落地
- config/insight_storage.json
- sql/insight_schema_v1.sql
- PostgreSQL database: oris_insight
- PostgreSQL schema: insight

## 已创建核心表
- company
- competitor_set
- competitor_set_member
- source
- source_snapshot
- evidence_item
- metric_observation
- analysis_run
- report_artifact
- citation_link
- delivery_task
- watch_task
- alert_event
- insight_schema_version

## 固定约束
1. 业务常量优先放配置文件或数据库，不散落在脚本
2. 数据库连接信息走 config + secrets
3. 正式报告主件为 Word
4. Excel 作为辅助明细与评分底表
5. 下载分发通道支持 Feishu，后续扩展 Qbot
