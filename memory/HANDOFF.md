# HANDOFF.md

## 当前交接点
ORIS 的 OpenClaw 基础设施、OpenRouter 接入、Feishu 通道与 systemd 常驻运行已完成。

## 当前事实
- `oris-openclaw.service` 正常运行
- `OPENROUTER_API_KEY` 已通过 `/etc/oris/openclaw.env` 持久化
- Feishu WebSocket 已接通
- pairing 已批准
- 飞书消息已进入 agent session
- 当前回复阶段触发 OpenClaw ByteString / Unicode 编码错误
- 当前问题判断为上游兼容性问题，不是部署层问题

## 下一步
1. 将当前状态固化到 GitHub
2. 准备上游 issue 复现材料
3. 评估临时替代方案：
   - 继续用 ChatGPT/Codex 作为主研发入口
   - OpenClaw 暂保留为基础设施与后续通道试验环境
4. 在上游修复前，不把飞书通道作为稳定商用入口
\n