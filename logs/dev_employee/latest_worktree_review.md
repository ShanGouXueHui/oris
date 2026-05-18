# Dev Employee Worktree Review

- generated_at: `2026-05-18T19:50:03.026460+00:00`
- planning_packet_path: `logs/dev_employee/latest_planning_packet.json`
- blocking_tracked_count: `1`
- blocking_untracked_count: `0`
- legacy_review_untracked_count: `6`

## Blocking tracked diffs

### `config/insight_entity_registry.json`

Diff stat:

```text
config/insight_entity_registry.json | 386 ++++++++++++++++++++++++++++++++++++
 1 file changed, 386 insertions(+)
```

Diff:

```diff
diff --git a/config/insight_entity_registry.json b/config/insight_entity_registry.json
index 521678c..f9020ed 100644
--- a/config/insight_entity_registry.json
+++ b/config/insight_entity_registry.json
@@ -281,6 +281,392 @@
           "official_flag": true
         }
       ]
+    },
+    {
+      "name": "Mercedes-Benz Group",
+      "aliases": [
+        "奔驰",
+        "梅赛德斯-奔驰",
+        "Mercedes-Benz",
+        "Mercedes"
+      ],
+      "role_tags": [
+        "company",
+        "automotive_oem",
+        "luxury_auto"
+      ],
+      "domain": "group.mercedes-benz.com",
+      "region": "global",
+      "focus_profile": "automotive_oem",
+      "sources": [
+        {
+          "source_name": "Mercedes-Benz Group Investor Relations",
+          "source_type": "investor_relations",
+          "url": "https://group.mercedes-benz.com/investors/",
+          "title": "Investor Relations",
+          "publisher": "Mercedes-Benz Group",
+          "official_flag": true
+        },
+        {
+          "source_name": "Mercedes-Benz Group Annual Reports",
+          "source_type": "annual_report",
+          "url": "https://group.mercedes-benz.com/investors/reports-news/annual-reports/download/",
+          "title": "Annual Reports",
+          "publisher": "Mercedes-Benz Group",
+          "official_flag": true
+        },
+        {
+          "source_name": "Mercedes-Benz Group Annual Reports 2025",
+          "source_type": "annual_report",
+          "url": "https://group.mercedes-benz.com/investors/reports-news/annual-reports/2025/",
+          "title": "Results and Annual Report 2025",
+          "publisher": "Mercedes-Benz Group",
+          "official_flag": true
+        },
+        {
+          "source_name": "Mercedes-Benz Group Annual Report 2025 PDF",
+          "source_type": "annual_report",
+          "url": "https://group.mercedes-benz.com/documents/investors/reports/annual-report/mercedes-benz/mercedes-benz-annual-report-2025-incl-combined-management-report-mbg-ag.pdf",
+          "title": "Mercedes-Benz Group Annual Report 2025 PDF",
+          "publisher": "Mercedes-Benz Group",
+          "official_flag": true
+        },
+        {
+          "source_name": "Mercedes-Benz Group FY2025 Capital Market Presentation PDF",
+          "source_type": "investor_relations",
+          "url": "https://group.mercedes-benz.com/dokumente/investoren/praesentationen/mercedes-benz-ir-capitalmarketpresentation-fy-2025.pdf",
+          "title": "Capital Market Presentation FY 2025 PDF",
+          "publisher": "Mercedes-Benz Group",
+          "official_flag": true
+        }
+      ],
+      "default_related_entities": {
+        "competitors": [
+          "BMW Group",
+          "Audi",
+          "Tesla",
+          "Porsche"
+        ],
+        "industry_peers": [
+          "BMW Group",
+          "Audi",
+          "Tesla",
+          "Porsche"
+        ]
+      }
+    },
+    {
+      "name": "BMW Group",
+      "aliases": [
+        "BMW",
+        "BMW Group",
+        "宝马"
+      ],
+      "role_tags": [
+        "company",
+        "automotive_oem",
+        "luxury_auto"
+      ],
+      "domain": "bmwgroup.com",
+      "region": "global",
+      "focus_profile": "automotive_oem",
+      "sources": [
+        {
+          "source_name": "BMW Group Investor Relations",
+          "source_type": "investor_relations",
+          "url": "https://www.bmwgroup.com/en/investor-relations.html",
+          "title": "Investor Relations",
+          "publisher": "BMW Group",
+          "official_flag": true
+        },
+        {
+          "source_name": "BMW Group Company Reports",
+          "source_type": "annual_report",
+          "url": "https://www.bmwgroup.com/en/investor-relations/company-reports.html",
+          "title": "Company Reports",
+          "publisher": "BMW Group",
+          "official_flag": true
+        }
+      ],
+      "default_related_entities": {
+        "competitors": [
+          "Mercedes-Benz Group",
+          "Audi",
+          "Tesla",
+          "Porsche"
+        ]
+      }
+    },
+    {
+      "name": "Audi",
+      "aliases": [
+        "Audi",
+        "奥迪"
+      ],
+      "role_tags": [
+        "company",
+        "automotive_oem",
+        "luxury_auto"
+      ],
+      "domain": "audi.com",
+      "region": "global",
+      "focus_profile": "automotive_oem",
+      "sources": [
+        {
+          "source_name": "Audi Investor Relations",
+          "source_type": "investor_relations",
+          "url": "https://www.audi.com/en/company/investor-relations/",
+          "title": "Investor Relations",
+          "publisher": "Audi",
+          "official_flag": true
+        },
+        {
+          "source_name": "Audi Financial Publications",
+          "source_type": "annual_report",
+          "url": "https://www.audi.com/en/company/investor-relations/financial-publications/",
+          "title": "Financial Publications",
+          "publisher": "Audi",
+          "official_flag": true
+        }
+      ],
+      "default_related_entities": {
+        "competitors": [
+          "Mercedes-Benz Group",
+          "BMW Group",
+          "Tesla",
+          "Porsche"
+        ]
+      }
+    },
+    {
+      "name": "Tesla",
+      "aliases": [
+        "Tesla",
+        "特斯拉"
+      ],
+      "role_tags": [
+        "company",
+        "automotive_oem",
+        "ev_company"
+      ],
+      "domain": "tesla.com",
+      "region": "global",
+      "focus_profile": "automotive_oem",
+      "sources": [
+        {
+          "source_name": "Tesla Investor Relations",
+          "source_type": "investor_relations",
+          "url": "https://ir.tesla.com/",
+          "title": "Investor Relations",
+          "publisher": "Tesla",
+          "official_flag": true
+        },
+        {
+          "source_name": "Tesla Impact Report",
+          "source_type": "annual_report",
+          "url": "https://www.tesla.com/impact",
+          "title": "Impact Report",
+          "publisher": "Tesla",
+          "official_flag": true
+        }
+      ],
+      "default_related_entities": {
+        "competitors": [
+          "Mercedes-Benz Group",
+          "BMW Group",
+          "Audi",
+          "Porsche"
+        ]
+      }
+    },
+    {
+      "name": "Porsche",
+      "aliases": [
+        "Porsche",
+        "保时捷"
+      ],
+      "role_tags": [
+        "company",
+        "automotive_oem",
+        "luxury_auto"
+      ],
+      "domain": "porsche.com",
+      "region": "global",
+      "focus_profile": "automotive_oem",
+      "sources": [
+        {
+          "source_name": "Porsche Investor Relations",
+          "source_type": "investor_relations",
+          "url": "https://investorrelations.porsche.com/",
+          "title": "Investor Relations",
+          "publisher": "Porsche",
+          "official_flag": true
+        }
+      ],
+      "default_related_entities": {
+        "competitors": [
+          "Mercedes-Benz Group",
+          "BMW Group",
+          "Audi",
+          "Tesla"
+        ]
+      }
+    },
+    {
+      "name": "Tencent",
+      "aliases": [
+        "腾讯",
+        "Tencent"
+      ],
+      "role_tags": [
+        "company",
+        "internet_platform"
+      ],
+      "domain": "tencent.com",
+      "region": "China",
+      "focus_profile": "internet_platform",
+      "sources": [
+        {
+          "source_name": "Tencent Investors",
+          "source_type": "investor_relations",
+          "url": "https://www.tencent.com/en-us/investors.html",
+          "title": "Investors",
+          "publisher": "Tencent",
+          "official_flag": true
+        },
+        {
+          "source_name": "Tencent Financial Reports",
+          "source_type": "annual_report",
+          "url": "https://www.tencent.com/en-us/investors/financial-reports.html",
+          "title": "Financial Reports",
+          "publisher": "Tencent",
+          "official_flag": true
+        },
+        {
+          "source_name": "Tencent 2025 Annual and Fourth Quarter Results PDF",
+          "source_type": "annual_report",
+          "url": "https://static.www.tencent.com/uploads/2026/03/18/e6a646796d0d869acc76271c9ee1a6a5.pdf",
+          "title": "Tencent Announces 2025 Annual and Fourth Quarter Results PDF",
+          "publisher": "Tencent",
+          "official_flag": true
+        },
+        {
+          "source_name": "Tencent 2025 Annual Results Presentation PDF",
+          "source_type": "investor_relations",
+          "url": "https://static.www.tencent.com/uploads/2026/03/18/2804dbdae364ca25b82d21bc8304f1d3.pdf",
+          "title": "2025 Fourth Quarter and Annual Results Presentation PDF",
+          "publisher": "Tencent",
+          "official_flag": true
+        }
+      ],
+      "default_related_entities": {
+        "competitors": [
+          "Alphabet",
+          "Meta",
+          "ByteDance"
+        ]
+      }
+    },
+    {
+      "name": "Alphabet",
+      "aliases": [
+        "Google",
+        "谷歌",
+        "Alphabet"
+      ],
+      "role_tags": [
+        "company",
+        "internet_platform",
+        "cloud_ai_platform"
+      ],
+      "domain": "abc.xyz",
+      "region": "global",
+      "focus_profile": "internet_platform",
+      "sources": [
+        {
+          "source_name": "Alphabet Investor Relations",
+          "source_type": "investor_relations",
+          "url": "https://abc.xyz/investor/",
+          "title": "Investor Relations",
+          "publisher": "Alphabet",
+          "official_flag": true
+        },
+        {
+          "source_name": "Alphabet FY2025 Results Page",
+          "source_type": "investor_relations",
+          "url": "https://abc.xyz/investor/news/news-details/2026/Alphabet-Announces-Fourth-Quarter-2025-and-Fiscal-Year-Results-2026-KEvZIMKBLS/default.aspx",
+          "title": "Alphabet Announces Fourth Quarter 2025 and Fiscal Year Results",
+          "publisher": "Alphabet",
+          "official_flag": true
+        },
+        {
+          "source_name": "Alphabet SEC Filings",
+          "source_type": "government_or_regulator",
+          "url": "https://abc.xyz/investor/sec-filings/",
+          "title": "Alphabet SEC Filings",
+          "publisher": "Alphabet",
+          "official_flag": true
+        },
+        {
+          "source_name": "Alphabet Earnings",
+          "source_type": "investor_relations",
+          "url": "https://abc.xyz/investor/earnings/",
+          "title": "Alphabet Earnings",
+          "publisher": "Alphabet",
+          "official_flag": true
+        }
+      ],
+      "default_related_entities": {
+        "competitors": [
+          "Tencent",
+          "Microsoft",
+          "Meta",
+          "Amazon"
+        ]
+      }
+    },
+    {
+      "name": "智谱",
+      "aliases": [
+        "智谱",
+        "Zhipu",
+        "Zhipu AI",
+        "Z.AI",
+        "GLM"
+      ],
+      "role_tags": [
+        "company",
+        "foundation_model_company"
+      ],
+      "domain": "zhipuai.cn",
+      "region": "China",
+      "focus_profile": "foundation_model_company",
+      "sources": [
+        {
+          "source_name": "Zhipu Official Website",
+          "source_type": "official_website",
+          "url": "https://www.zhipuai.cn/en",
+          "title": "Zhipu Official Website",
+          "publisher": "智谱",
+          "official_flag": true
+        },
+        {
+          "source_name": "Zhipu Open Platform",
+          "source_type": "product_page",
+          "url": "https://bigmodel.cn/",
+          "title": "ZHIPU AI OPEN PLATFORM",
+          "publisher": "智谱",
+          "official_flag": true
+        }
+      ],
+      "default_related_entities": {
+        "competitors": [
+          "OpenAI",
+          "Anthropic",
+          "DeepSeek",
+          "阿里云"
+        ]
+      }
     }
   ]
 }
```

## Blocking untracked

```text
<none>
```

## Legacy review untracked

```text
inputs/manual_refresh/
scripts/feishu_account_strategy_trigger.py
scripts/run_account_strategy_case_pipeline.py
scripts/run_account_strategy_trigger_loop.sh
scripts/run_insight_queue_worker_loop.sh.disabled
skills/official_source_ingest_skill/runner_providerized.py
```
