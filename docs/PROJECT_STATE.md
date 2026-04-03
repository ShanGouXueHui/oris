# PROJECT_STATE.md

## 当前日期
2026-04-03

## 当前阶段
ORIS v1：OpenClaw 运行层与飞书通道接通，进入上游兼容性问题处理阶段

## 当前状态
- deploy 用户、GitHub SSH、仓库规则层、OpenClaw CLI、OpenRouter onboard 已完成
- OpenClaw Gateway 已改为 systemd 系统服务 `oris-openclaw.service`
- OpenRouter key 已通过 `/etc/oris/openclaw.env` 持久化，不再需要手工输入
- Gateway 正常监听 `127.0.0.1:18789`
- Feishu WebSocket 通道已接通
- 飞书 pairing 已批准
- 飞书私聊消息已能进入 agent session

## 当前阻塞
- OpenClaw 当前版本在回复链路触发 ByteString / Unicode 编码错误
- 表现为飞书端返回：
  `Cannot convert argument to a ByteString because the character at index 7 has a value of 25226 which is greater than 255.`
- 该问题已判断为上游 OpenClaw 兼容性 / 编码问题，而非当前服务器部署问题

## 当前结论
- 基础设施与飞书通道已基本打通
- 当前不应继续把时间消耗在服务器侧盲调
- 后续应转为：
  1. 跟踪/提交 OpenClaw 上游 issue
  2. 评估临时替代路径
  3. 在上游修复前，不将飞书通道作为稳定生产入口
\n