# account_strategy_skill

顶层业务 skill，用于处理如下复杂商务洞察题：
- 伙伴 + 云厂商 + 客户 + 竞争对手 的四方图谱分析
- 联合解决方案设计
- Top 账户突破策略
- 商务 Word / Excel / PPT 交付编排

当前阶段定位：
- 作为 ORIS 洞察 AI 员工的顶层业务入口
- 编排底层 skill：
  - official_source_ingest_skill
  - company_profile_skill
  - competitor_research_skill
  - report_build_skill

当前输出：
- case graph
- source policy
- analysis sections
- capability mapping
- execution plan
- artifact plan

后续升级方向：
- 真正调度底层 skill 执行
- 写入 analysis_run / recommendation_case / capability_mapping 等实体
- 自动触发 Word / Excel / PPT 生成与 delivery_task
