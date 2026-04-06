# Decision: 报告产物注册与分发队列接入数据库

## 日期
2026-04-06

## 决策
ORIS 正式把 Word / Excel / manifest / zip 报告产物注册进 `insight.report_artifact`，
并把 Feishu / Qbot 的下载分发任务注册进 `insight.delivery_task`。

## 目的
1. 报告产物从“本地文件”升级为“系统资产”
2. 下载分发从临时动作升级为“可追踪任务”
3. 后续 Feishu / Qbot 文件发送可直接消费任务队列
4. 支撑审计、补发、失败重试、生命周期管理

## 配置优先
固定运行参数放在：
- config/report_runtime.json

脚本只读配置，不在代码中散落渠道、路径、mime、artifact kind 等常量。

## 当前范围
- 已支持注册：
  - Word 报告
  - Excel 评分底表
  - 下载 manifest
  - 交付 zip 包
- 已支持创建待分发任务：
  - Feishu
  - Qbot

## 当前边界
当前完成的是“注册 + 排队”。
Feishu / Qbot 的真实文件下载发送器，后续再接到 delivery_task 消费流程。
