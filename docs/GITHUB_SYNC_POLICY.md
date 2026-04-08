# ORIS GitHub Sync Policy

## 1. 定位
GitHub 是 ORIS 的权威长期记忆、主链路代码来源、跨对话续航底座。  
部署环境中的仓库应尽量与 `origin/main` 保持一致，不允许长期依赖“只存在于服务器本地”的隐性实现。

---

## 2. 文件分层

### A. 必须纳入 GitHub 主线
- 业务源码：`scripts/` `skills/` `app/` `sql/`
- 稳定非敏感配置：`config/`
- 架构/规则/决策/交接文档：`docs/` `memory/`
- 少量经验证的机器可读基线快照（例如 `orchestration/active_routing.json`），但仅在“基线变更被确认”时提交

### B. 可存在于本地，但默认不提交
- `outputs/` 下的本地产物
- 一次性实验脚本
- 临时 case 文件
- 调试样本

### C. 严禁提交
- secrets / token / key / private cert
- `.env` 与衍生文件
- `jsonl` 日志
- `lock / out / pid / state` 运行噪音
- 临时备份 `*.bak_*`
- 数据库导出、临时结果快照、回放文件

---

## 3. 当前 2026-04-08 漂移分类

### 应进入主链路评审的候选
- `config/company_entity_detection.json`
- `config/company_focus_config.json`
- `config/entity_resolution.json`
- `config/insight_delivery_config.json`
- `scripts/build_company_focus_prompt.py`
- `scripts/company_entity_detector.py`
- `scripts/feishu_insight_enqueue.py`
- `scripts/insight_queue_worker.py`
- `scripts/render_mobile_insight.py`

### 暂不纳入本轮主链路的候选
- `scripts/feishu_account_strategy_trigger.py`
- `scripts/run_account_strategy_case_pipeline.py`
- `scripts/run_account_strategy_trigger_loop.sh`
- `scripts/run_insight_queue_worker_loop.sh.disabled`

### 明确属于运行噪音 / 不应提交
- `orchestration/*.jsonl`
- `orchestration/*.lock`
- `orchestration/*.out`
- `orchestration/restore_provider_files.json`

### 需单独审慎处理的生成快照
- `orchestration/active_routing.json`

规则：
- `active_routing.json` 可以跟踪，但只在“策略/模型基线确认变化”时提交
- 不接受“每次 probe 都提交一次 active_routing”的噪音式同步

---

## 4. 同步流程

### 标准顺序
1. `git fetch origin`
2. 检查本地漂移
3. 区分：主链路候选 / 运行噪音 / 实验残留
4. 先补配置与文档，再改代码
5. 自检验证通过
6. 更新 `docs/PROJECT_STATE.md`、`memory/HANDOFF.md`、必要时新增 `docs/DECISIONS/*`
7. `git add` → `git commit` → `git push`
8. 部署环境验证
9. 保证 `git status` 回归干净或仅剩明确批准的快照文件

---

## 5. 商用工程要求
- GitHub 必须能独立表达当前系统设计与当前主阻塞
- 新对话必须先读 GitHub 文档，而不是依赖聊天历史
- 不允许用运行日志代替正式文档
- 不允许用临时补丁掩盖主问题
- 不允许长期保留未归档、未分类、未提交的核心代码漂移

---

## 6. 本轮固定优先级
1. 把通用公司识别能力正式接入主链路
2. 保证识别失败时明确阻断，不再产出垃圾正文
3. Feishu 只发送真实洞察正文或明确阻断提示
4. 最后再继续扩展 account_strategy / 其他高级场景
