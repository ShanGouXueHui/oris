# Decision: Feishu delivery executor is now live for insight delivery_task

## Date
2026-04-06

## Conclusion
ORIS 已完成 Feishu 报告下载链接分发执行器闭环：
- `insight.delivery_task` 的 Feishu pending 任务可被真实消费
- 执行器基于真实表结构运行：
  - `channel_type`
  - `channel_target`
  - `delivery_mode`
  - `download_url`
  - `delivery_result_json`
- Feishu 发送目标采用 `chat_id`
- Feishu 发送通道采用正式 OpenAPI：
  - `tenant_access_token`
  - `POST /open-apis/im/v1/messages?receive_id_type=chat_id`

## Evidence
验证结果：
- dry-run 成功拿到：
  - `target_used = oc_2088cbc62e2aa06533848ec7b7b06415`
  - `has_tenant_access_token = true`
  - `mode = send`
- 实发成功并回写 `sent + delivered_at`：
  - task_id: `17 / 19 / 23 / 25 / 29 / 31`
- Feishu 剩余 pending：
  - `pending_count = 0`

## Historical cleanup
以下任务已确认属于历史脏数据，不属于当前下载链接分发闭环失败：
- `21`
- `27`

原因：
- 对应 artifact 为 `download manifest json`
- `downloadable_flag = false`
- 任务缺少：
  - `delivery_mode`
  - `delivery_code`
  - `download_url`

因此保留 `failed`，并在 `delivery_result_json.historical_cleanup` 中写明：
- `non_downloadable_json_manifest_should_not_be_delivered`

## Code/config changes
本轮已落地：
- `config/report_runtime.json`
  - 新增 `delivery`
  - 新增 `channels.feishu`
  - 新增 `channels.qbot`
  - 新增 `delivery.channel_targets.feishu.default_target`
- `scripts/register_report_delivery.py`
  - 新任务不再把 `channel_target` 固定写成 `None`
  - 改为从 runtime config 读取默认目标
- `scripts/delivery_executor.py`
  - 改为匹配真实 `insight.delivery_task` schema
  - Feishu 复用 `scripts/feishu_send_executor_skeleton.py`
  - Qbot 保留 generic webhook 执行入口

## Next
下一优先级建议：
1. 补 Qbot delivery executor 配置并验证
2. 为 `company_profile_skill / competitor_research_skill / official_source_ingest_skill / report_build_skill` 建 scaffold
3. 把 insight DB 从“有表结构”推进到“持续沉淀真实 company/source/evidence/metric 数据”
