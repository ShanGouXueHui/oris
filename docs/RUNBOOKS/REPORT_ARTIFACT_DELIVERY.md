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
