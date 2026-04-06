# 2026-04-06 Report download channel bootstrap

## Decision
ORIS 先采用“签名下载链接”作为报告交付的统一底座，而不是一开始就把 Word / Excel / Zip 直接上传到各渠道。

## Why
1. 当前 `report_artifact` 与 `delivery_task` 已经入库成功，但 `channel_target` 还未在全链路稳定沉淀。
2. 先统一下载交付，可以把“产物治理”和“渠道执行”解耦。
3. Feishu 与后续 Qbot 都可以复用同一个下载地址生成逻辑。

## Result
- 新增 `oris-report-download.service`
- 新增公网路由 `/oris-download/...`
- 新增 `materialize_report_delivery_links.py`
- `delivery_task.delivery_result_json` 开始承载签名下载链接与到期时间

