# PROJECT_STATE.md

## 当前日期
2026-04-03

## 当前阶段
ORIS v1：规则层完成基线初始化，进入 OpenClaw 运行层与渠道接入准备阶段

## 当前状态
- GitHub 仓库已创建并完成第一版规则层基线提交
- deploy 用户已创建，具备 sudo 能力
- admin 侧已创建 `todeploy` 快捷命令
- deploy 用户已完成 Ubuntu 基础环境初始化
- GitHub SSH Key 已配置完成，可正常 push/pull
- OpenClaw CLI 已安装完成
- OpenRouter 已完成 onboard，配置文件生成于 `~/.openclaw/openclaw.json`
- OpenClaw Gateway 已成功运行
- 当前运行方式：前台自管进程 / `nohup openclaw gateway run --port 18789`
- 当前监听地址：`127.0.0.1:18789`
- 本机健康检查通过：`curl -I http://127.0.0.1:18789/` 返回 `HTTP/1.1 200 OK`

## 已确认问题
- 当前服务器 `user-systemd` / DBus 不可用
- 因此 `openclaw onboard --install-daemon` 的 user service 安装失败
- 目前不适合依赖 `systemd --user` 维持 OpenClaw Gateway

## 当前结论
- OpenClaw 主链路已打通
- 当前不需要开放公网 18789 端口
- 如需手机直接访问，应采用 Nginx 反代 + HTTPS + 鉴权，而不是直接暴露 Gateway 端口
- 下一优先级是渠道接入，首选飞书，微信作为后备

## 下一步
1. 将当前运行状态与决策沉淀到仓库
2. 形成 OpenClaw 运行与巡检 runbook
3. 启动飞书接入
4. 后续再决定是否补 system-level service 或 Nginx 反代

