# OPENCLAW_RUNTIME.md

## 当前运行方式
ORIS 当前采用前台自管进程运行 OpenClaw Gateway。

## 启动命令
```bash
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export NODE_COMPILE_CACHE=/var/tmp/openclaw-compile-cache
mkdir -p /var/tmp/openclaw-compile-cache
export OPENCLAW_NO_RESPAWN=1
export OPENROUTER_API_KEY=你的真实key
nohup openclaw gateway run --port 18789 > ~/openclaw-gateway.log 2>&1 &
echo $! > ~/openclaw-gateway.pid
```

## 检查命令
```bash
cat ~/openclaw-gateway.pid
ps -fp "$(cat ~/openclaw-gateway.pid)"
openclaw gateway status
curl -I http://127.0.0.1:18789/
tail -n 80 ~/openclaw-gateway.log
```

## 停止命令
```bash
kill "$(cat ~/openclaw-gateway.pid)"
rm -f ~/openclaw-gateway.pid
```

## 当前限制
- 当前不依赖 `systemd --user`
- 当前仅 loopback 监听，不提供公网直连
- 若需手机访问，建议通过 Nginx 反代与鉴权实现

