# 2026-04-06 Report download public route

## Decision
为报告分发链路新增公网下载路由 `/oris-download/...`，并在 nginx 中显式关闭 Basic Auth。

## Why
当前 ORIS 的报告产物已经完成：
1. report_artifact 入库
2. delivery_task 排队
3. signed download link 物化

但若公网下载路由仍继承 control.orisfy.com 的 Basic Auth，则终端用户无法直接下载 Word / Excel / Zip 产物。

## Result
- `/oris-download/health` 对公网免 Basic Auth
- `/oris-download/<artifact_code>?expires=...&sig=...` 对公网免 Basic Auth
- 下载仍受签名与过期时间控制，不是裸露静态目录
- Feishu / Qbot 后续只需发送下载链接，不必直接承载文件治理逻辑
\n