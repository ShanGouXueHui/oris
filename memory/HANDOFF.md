# HANDOFF.md

## 当前交接点
ORIS 已完成规则层基线、GitHub 接入、OpenClaw 基础安装与本机运行验证。

## 当前事实
- OpenClaw CLI 已安装
- OpenRouter onboard 已完成
- `~/.openclaw/openclaw.json` 已生成
- Gateway 当前通过前台自管进程运行
- 当前监听 `127.0.0.1:18789`
- 本机 `curl -I http://127.0.0.1:18789/` 返回 200
- 当前服务器 `user-systemd` / DBus 不可用
- 当前不开放公网 18789
- 若需手机访问，应走 Nginx 反代 + HTTPS + 鉴权
- 渠道接入优先级：飞书 > 微信

## 下一步
1. 提交本次运行状态文档更新
2. 建立 OpenClaw runtime runbook
3. 启动飞书渠道接入
4. 如有必要，后续补 system-level service 或 supervisor 管理

## 风险提醒
- 不要提交 `~/.openclaw/openclaw.json` 或任何真实密钥
- 不要直接暴露 18789 到公网
- 在反代与鉴权未完成前，不要将 Gateway 改为非 loopback 监听

