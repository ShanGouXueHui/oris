# 2026-04-06 Insight Storage Compatibility Fix

## 背景
report download security v2 已提交，但运行期 helper 对 `config/insight_storage.json` 的配置口径兼容不完整，
导致 DB 连接失败，继而影响 migration、delivery sync、download audit 验证。

## 本次修复
1. 对 `config/insight_storage.json` 进行统一归一化，补出标准 `db` 结构。
2. `scripts/lib/report_delivery_runtime.py` 支持多种历史口径：
   - `db`
   - `postgres`
   - `database`
   - `storage.db`
   - `storage.postgres`
   - DSN / URL
3. 恢复 v2 migration、delivery sync、signed download、download audit 验证链路。

## 结论
这是配置兼容层修复，不改变 ORIS insight / report download 的总体架构方向。
