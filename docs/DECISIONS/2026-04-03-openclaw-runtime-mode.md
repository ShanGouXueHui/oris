# 2026-04-03 OpenClaw runtime mode

## 决策
当前服务器上，ORIS 的 OpenClaw Gateway 暂采用“前台自管进程”运行模式，不依赖 `systemd --user`。

## 原因
- `openclaw onboard --install-daemon` 已成功生成配置，但 gateway service install 失败
- 根因是当前纯 SSH 服务器环境下 `user-systemd` / DBus 不可用
- 继续强行修 user service，性价比低，且不影响当前主链路验证

## 当前运行方式
通过以下方式运行：
- `nohup openclaw gateway run --port 18789 > ~/openclaw-gateway.log 2>&1 &`
- Gateway 监听于 `127.0.0.1:18789`

## 结论
在当前阶段，前台自管进程模式足以支撑：
- OpenClaw 主链路验证
- OpenRouter 认证与模型调用
- 后续飞书渠道接入准备

## 后续选项
后续如需增强稳定性，可在以下方案中二选一：
1. system-level systemd service
2. Nginx + supervisor/pm2/系统服务 组合

## 安全边界
- 保持 loopback 监听
- 不直接开放 18789 公网访问
- 远程访问优先通过 SSH 隧道或 Nginx 反代 + HTTPS + 鉴权

