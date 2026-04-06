# 2026-04-06 Signed download auth model

## Decision
ORIS 公网下载接口保留认证，但不使用 nginx Basic Auth；改为签名链接认证。

## Why
Feishu / Qbot 面向终端用户分发 Word / Excel / Zip 产物时，若下载链路仍依赖站点级 Basic Auth，则用户体验不可用，且机器人无法自然闭环交付。

## Auth model
1. 管理面（控制台 / 管理 API）继续使用 Basic Auth
2. 下载面（/oris-download/）关闭 Basic Auth
3. 下载面改为：
   - artifact_code
   - expires
   - sig
   三元组签名认证
4. 服务端继续校验：
   - artifact 存在
   - downloadable_flag=true
   - 未过期
   - 签名正确
   - 可结合 delivery_task 做审计和后续限次下载

## Security stance
这不是匿名公开下载，而是 bearer-style signed URL download。
后续可升级为：
- 一次性 token
- 限次下载
- delivery_task 状态回写
- 下载审计日志
