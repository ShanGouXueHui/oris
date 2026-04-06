# 2026-04-06 Report Download Security v2

## 结论
把 ORIS 报告下载从 artifact_code 粗粒度签名，升级为 delivery_code 细粒度签名。

## 本次改动
1. delivery_task 增加 delivery_code / max_downloads / used_count / expires_at / revoke 字段
2. 新增 download_event 审计表
3. 下载服务改为按 delivery_code 校验签名
4. register_report_delivery.py 改为幂等同步，不再重复插 pending task
5. 对重复 pending task 做清理，并增加唯一索引

## 为什么这版更稳
- 一个 delivery task 对应一个下载链接
- 能区分 Feishu / Qbot 渠道
- 能限次、撤销、审计
- 重新跑同步脚本不会无限新增 pending 行
