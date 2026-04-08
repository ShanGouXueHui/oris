# ORIS Insight Delivery Policy

## 1. 目标
Feishu 聊天版结果必须体现 ORIS 的商用品质。  
允许发送的内容只有两类：
1. 真实洞察正文
2. 明确阻断提示

禁止发送：
- prompt 原文
- bootstrap 占位文
- renderer 异常堆栈
- “已跑通但先给你个占位内容”这类垃圾文本

---

## 2. 推荐链路
`feishu_insight_enqueue.py`
→ `insight_queue_worker.py`
→ `run_generic_insight_pipeline_plus.py`
→ `render_mobile_insight.py`
→ `send_feishu_text_message.py`

原则：
- ingress 负责入队，不负责重分析
- worker 负责串行消费与状态控制
- pipeline 负责真实洞察生成
- renderer 只负责最终聊天版格式化
- sender 只负责发送，不再夹带业务逻辑

---

## 3. 单实例规则
- `insight_queue_worker.py` 必须单实例运行
- lock 文件只能作为最低层防线
- 生产运行应以单一 systemd / supervisor 主入口为准
- 旧 loop launcher 若已退役，必须退出主链路，不能与 worker 并跑

---

## 4. 占位文本拦截
若命中任一条件，必须阻断：
- entity 缺失
- snapshot/evidence/metric 为空且不满足最小发送标准
- markdown 命中 placeholder blocklist
- renderer 输出为空或无效
- pipeline 返回明显属于调试/模板占位语句

拦截后：
- 向用户发送短阻断说明
- 记录 worker log
- 不得继续发送占位正文

---

## 5. 聊天版与正式件分层
### 聊天版
- 面向 Feishu 即时阅读
- 可分段发送
- 只保留高密度结论与关键证据

### 正式件
- Word：正式阅读版
- Excel：证据与明细底表
- PPT：商务沟通版

聊天版不是正式件的替代物，也不能拿 prompt 拼接冒充聊天版。

---

## 6. 配置治理
以下参数必须放在配置中：
- chunk limit
- render fail text
- placeholder blocklist
- delivery enable / disable
- queue behavior

当前建议配置文件：
- `config/insight_delivery_config.json`

---

## 7. 主链路退役要求
以下路径若仍存在，只能视为历史/实验路径，不得继续作为正式入口：
- 旧 direct trigger 直接发消息
- pipeline 内直接发送 Feishu 文本
- account_strategy 专用 trigger loop 冒充 generic insight 正式入口

---

## 8. 成功标准
同时满足以下条件，才算聊天链路通过：
- 正确识别 `target_company`
- official ingest / profile 真正写出实体相关数据
- renderer 输出非占位、非空文本
- Feishu 收到真实正文
- worker 日志可审计
