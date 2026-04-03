# 2026-04-03 Feishu ByteString blocker

## 决策
暂不继续在服务器侧盲调 OpenClaw 飞书回复异常。

## 原因
当前 systemd、Gateway、OpenRouter、Feishu WebSocket、pairing 均已打通。
飞书消息能够进入 agent session，但回复阶段出现 ByteString / Unicode 编码错误。

## 结论
该问题应按上游兼容性问题处理，而不是继续当作服务器部署问题处理。

## 执行策略
- 固化当前里程碑
- 保留现有服务状态
- 跟踪/提交上游 issue
- 上游未修复前，不把飞书作为稳定生产入口
\n