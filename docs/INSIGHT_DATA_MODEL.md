# ORIS 洞察数据模型（Insight Data Model）

## 1. 目标
本文件定义 ORIS 企业竞争力洞察所需的最小可用数据模型，服务于：
- 证据沉淀
- 引用追溯
- 时间序列分析
- 报告生成
- 下载分发
- 监控告警

默认数据库：PostgreSQL

---

## 2. 核心表设计

## 2.1 company
企业主体主表

建议字段：
- id
- company_code
- company_name
- company_name_en
- domain
- ticker
- exchange
- industry
- region
- is_target
- is_competitor
- status
- created_at
- updated_at

用途：
- 管理我方主体、竞品主体、产业链主体

---

## 2.2 competitor_set
竞对分析集合

建议字段：
- id
- set_code
- set_name
- target_company_id
- description
- scope_type
- created_at
- updated_at

用途：
- 定义某个分析任务的竞对范围

---

## 2.3 competitor_set_member
竞对集合成员表

建议字段：
- id
- competitor_set_id
- company_id
- role_type
- note
- created_at

用途：
- 管理 direct competitor / indirect competitor / benchmark peer

---

## 2.4 source
来源主表

建议字段：
- id
- source_code
- source_name
- source_type
- source_priority
- root_domain
- publisher
- api_name
- official_flag
- created_at
- updated_at

source_type 示例：
- official_website
- exchange_filing
- annual_report
- earnings_release
- government
- media
- research
- pdf
- social
- ecommerce
- api

---

## 2.5 source_snapshot
来源快照表

建议字段：
- id
- source_id
- company_id
- snapshot_type
- snapshot_title
- snapshot_url
- snapshot_time
- fetch_time
- content_hash
- raw_storage_path
- parsed_text_storage_path
- metadata_json
- created_at

用途：
- 保存某一时点的原始材料与快照
- 支撑“差异比对”“证据回溯”“链接引用”

---

## 2.6 evidence_item
证据表

建议字段：
- id
- source_snapshot_id
- company_id
- evidence_type
- evidence_title
- evidence_text
- evidence_number
- evidence_unit
- evidence_date
- confidence_score
- locator_json
- created_at

evidence_type 示例：
- revenue
- gross_margin
- shipment
- price
- feature_release
- management_statement
- market_share
- review_signal
- hiring_signal
- capex
- guidance

用途：
- 让证据从“原文材料”中被抽出并复用

---

## 2.7 metric_observation
指标观测表

建议字段：
- id
- company_id
- metric_code
- metric_name
- metric_value
- metric_unit
- period_type
- period_start
- period_end
- observation_date
- source_snapshot_id
- evidence_item_id
- normalization_rule
- created_at

用途：
- 用于结构化时间序列对比
- 支撑财务、价格、功能、流量、舆情等可比分析

---

## 2.8 citation_link
引用链表

建议字段：
- id
- request_id
- report_id
- claim_code
- evidence_item_id
- source_snapshot_id
- source_id
- citation_label
- citation_url
- citation_note
- created_at

用途：
- 把最终回答 / 报告里的结论和证据、来源绑定

---

## 2.9 analysis_run
分析运行表

建议字段：
- id
- run_code
- request_id
- analysis_type
- target_company_id
- competitor_set_id
- input_json
- result_json
- status
- started_at
- finished_at
- created_at

analysis_type 示例：
- competitor_landscape
- pricing_compare
- feature_compare
- management_compare
- financial_quality
- signal_monitor
- executive_briefing

---

## 2.10 report_artifact
报告产物表

建议字段：
- id
- artifact_code
- run_id
- request_id
- artifact_type
- title
- storage_path
- file_ext
- file_size
- manifest_json
- downloadable_flag
- created_at

artifact_type 示例：
- word_report
- excel_scoring
- ppt_brief
- zip_package
- json_manifest

---

## 2.11 delivery_task
分发任务表

建议字段：
- id
- artifact_id
- channel_type
- channel_target
- delivery_mode
- status
- delivery_result_json
- created_at
- delivered_at

channel_type 示例：
- feishu
- qbot
- http_download

---

## 2.12 watch_task
监控任务表

建议字段：
- id
- task_code
- task_name
- target_company_id
- competitor_set_id
- monitor_type
- schedule_expr
- enabled_flag
- config_json
- last_run_at
- next_run_at
- created_at
- updated_at

monitor_type 示例：
- price_change
- page_diff
- filing_update
- news_change
- hiring_signal
- review_spike

---

## 2.13 alert_event
告警事件表

建议字段：
- id
- watch_task_id
- company_id
- alert_type
- severity
- alert_title
- alert_summary
- trigger_value
- threshold_value
- payload_json
- created_at

---

## 3. 配置治理要求
以下内容不得写死在脚本里，应进入 config 或数据库：
- source priority
- metric code 字典
- evidence type 字典
- report 模板名
- 渠道下载策略
- 告警阈值
- schedule 频率
- 评分规则
- 竞对集合默认口径

---

## 4. 最小落地顺序
第一批先建：
1. company
2. competitor_set
3. competitor_set_member
4. source
5. source_snapshot
6. evidence_item
7. metric_observation
8. citation_link
9. analysis_run
10. report_artifact

第二批再补：
11. delivery_task
12. watch_task
13. alert_event

---

## 5. 设计原则
- 一切正式结论都应可回链到 citation_link
- 一切 citation_link 都应能回链到 evidence_item / source_snapshot
- 一切结构化数字都应尽量进入 metric_observation
- 一切正式交付文件都进入 report_artifact
- 一切对外下载动作都进入 delivery_task
