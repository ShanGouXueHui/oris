# ORIS Config Governance v2

## 1. 总原则
常量、规则、阈值必须按“敏感性 + 稳定性 + 调整频率”分层管理。  
不允许把业务常量继续散落在脚本里。

---

## 2. 配置层级

### Layer 1: Secrets
敏感值禁止写入 GitHub 仓库代码或非敏感配置文件。

当前 secret store：
- `~/.openclaw/secrets.json`

示例：
- ORIS API bearer token
- provider API keys
- channel app secrets
- private key / cert

### Layer 2: Stable repo config
稳定、非敏感、可版本控制的运行配置，放在 `config/`。

示例：
- bridge runtime
- entity detection rules
- delivery rules
- company focus rules
- insight storage non-secret blocks
- routing policy machine-readable inputs

### Layer 3: Generated baseline snapshots
自动生成、但在特定时点可作为“已确认基线”的文件。  
这些文件不是每次运行都要提交，只在“被确认有记录价值”时提交。

示例：
- `orchestration/active_routing.json`

### Layer 4: Runtime noise
运行时日志、lock、out、临时 state，不进入 GitHub。

示例：
- `orchestration/*.jsonl`
- `orchestration/*.lock`
- `orchestration/*.out`
- 一次性 state / restore 文件

### Layer 5: DB / Admin UI
高频运营规则、动态调参项，后续迁移到数据库或管理端。

示例：
- routing keyword tuning
- reply policy tuning
- bridge routing overrides
- threshold tuning
- allowlist / blocklist 运营规则

---

## 3. Commit 规则
### 必须提交
- 新增正式配置文件
- 配置 schema 变化
- 被确认的基线快照
- 与配置相关的文档更新

### 默认不提交
- runtime 日志
- locks / out
- 本地输出产物
- 临时回放文件

---

## 4. 编码规则
新增 bridge / insight / runtime 代码时：
1. 不要引入新的硬编码业务常量
2. 优先复用 `config/*`
3. 敏感值走 `secrets.json`
4. 高频运营调优项预留 DB / Admin UI 演进空间
5. 若新增配置文件，必须同步更新 docs 与 handoff

---

## 5. 执行规则
脚本应兼容从项目根目录直接执行，例如：
- `python3 scripts/openclaw_bridge_to_oris.py`
- `python3 scripts/bridge_feishu_to_oris.py`
- `python3 scripts/insight_queue_worker.py`

---

## 6. 商用治理要求
- 配置变更必须可审计
- 配置文件名与用途必须清晰
- 一个规则只应有一个权威配置来源
- 不接受脚本私藏第二份口径
