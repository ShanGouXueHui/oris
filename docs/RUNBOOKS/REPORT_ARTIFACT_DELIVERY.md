# REPORT_ARTIFACT_DELIVERY

## 配置文件
- config/report_runtime.json

## 注册脚本
- scripts/register_report_delivery.py

## 功能
1. 扫描 outputs/evals 下最新报告产物
2. 注册到 insight.report_artifact
3. 为 Feishu / Qbot 创建待分发 delivery_task

## 执行命令
python3 scripts/register_report_delivery.py

## 当前产物范围
- *.docx
- *.xlsx
- *.json
- *.zip

## 后续下一步
1. Feishu 文件发送器消费 delivery_task
2. Qbot 文件发送器消费 delivery_task
3. report_artifact 增加生命周期字段（下载次数、过期时间、清理标记）
4. delivery_task 增加重试次数、失败原因、最终投递状态


## Schema compatibility note (2026-04-06)

- `insight.delivery_task` 当前表结构要求 `channel_type`。
- 报告注册脚本不得在代码中硬编码渠道类型常量。
- 渠道类型映射统一放在 `config/report_runtime.json -> delivery.channel_type_map`。
- 当前默认映射：
  - `feishu -> feishu`
  - `qbot -> qbot`
- 若后续新增下载渠道，先补配置，再执行注册与分发脚本。


## Download delivery channel bootstrap (2026-04-06)

当前报告分发采用两段式设计：

1. `report_artifact` / `delivery_task` 先完成产物登记与待分发排队
2. `oris-report-download.service` 提供带签名、带过期时间的下载链接
3. `materialize_report_delivery_links.py` 把 pending 任务物化为 `download_link`
4. 后续 Feishu / Qbot 执行器只负责把链接发给对应渠道目标

当前设计目的：
- 先打通“可下载交付”
- 再叠加“渠道发送执行器”
- 避免把文件上传逻辑、渠道协议逻辑、产物治理逻辑混在一起

