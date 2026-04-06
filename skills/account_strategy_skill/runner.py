#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = ROOT / "config" / "insight_skill_runtime.json"
OFFICIAL_INGEST_RUNNER = ROOT / "skills" / "official_source_ingest_skill" / "runner.py"
COMPETITOR_RUNNER = ROOT / "skills" / "competitor_research_skill" / "runner.py"

sys.path.insert(0, str(ROOT / "scripts"))
from lib.report_delivery_runtime import db_connect  # noqa: E402

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def ts_compact():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def slugify(value: str):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", value or "").strip("-").lower()
    return s or "account-strategy"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def skill_cfg():
    data = load_json(RUNTIME_PATH)
    return (((data.get("skills") or {}).get("account_strategy_skill")) or {})

def normalize_case(req: dict):
    return {
        "case_code": req.get("case_code") or f"account-strategy-{ts_compact()}",
        "analysis_type": req.get("analysis_type") or "account_strategy",
        "partner": req.get("partner") or {},
        "cloud_vendor": req.get("cloud_vendor") or {},
        "customers": req.get("customers") or [],
        "competitor_case_path": req.get("competitor_case_path"),
        "dimensions": req.get("dimensions") or [],
        "questions": req.get("questions") or [],
        "required_artifacts": req.get("required_artifacts") or ["word", "excel", "ppt"]
    }

def build_ingest_payload(entity: dict):
    return {
        "entity": entity.get("name"),
        "domain": entity.get("domain"),
        "region": entity.get("region") or "global",
        "time_range": "latest",
        "sources": entity.get("sources") or []
    }

def run_runner(runner_path: Path, payload: dict, dry_run: bool):
    cmd = ["/usr/bin/python3", str(runner_path)]
    if dry_run:
        cmd.append("--dry-run")
    cmd += ["--input-json", json.dumps(payload, ensure_ascii=False)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {
            "ok": False,
            "error": (result.stderr or result.stdout or "").strip()[:4000],
            "payload": payload
        }
    try:
        return {"ok": True, "data": json.loads(result.stdout)}
    except Exception as e:
        return {
            "ok": False,
            "error": f"non_json_output: {e}",
            "stdout_preview": result.stdout[:2000],
            "payload": payload
        }

def fetch_company_by_domain_or_name(cur, name: str | None, domain: str | None):
    if domain:
        cur.execute("""
            SELECT id, company_code, company_name, domain, region, status
            FROM company
            WHERE domain = %s
            ORDER BY id DESC
            LIMIT 1
        """, (domain,))
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "company_code": row[1],
                "company_name": row[2],
                "domain": row[3],
                "region": row[4],
                "status": row[5]
            }
    if name:
        cur.execute("""
            SELECT id, company_code, company_name, domain, region, status
            FROM company
            WHERE lower(company_name) = lower(%s)
            ORDER BY id DESC
            LIMIT 1
        """, (name,))
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "company_code": row[1],
                "company_name": row[2],
                "domain": row[3],
                "region": row[4],
                "status": row[5]
            }
    return None

def fetch_entity_db_view(cur, company_id: int):
    cur.execute("""
        SELECT id, run_code, request_id, analysis_type, target_company_id
        FROM analysis_run
        WHERE target_company_id = %s
        ORDER BY id DESC
        LIMIT 20
    """, (company_id,))
    analysis_runs = [
        {
            "id": r[0],
            "run_code": r[1],
            "request_id": r[2],
            "analysis_type": r[3],
            "target_company_id": r[4]
        }
        for r in cur.fetchall()
    ]

    cur.execute("""
        SELECT ss.id, ss.source_id, ss.company_id, ss.snapshot_type, ss.snapshot_title,
               ss.snapshot_url, ss.raw_storage_path, ss.parsed_text_storage_path, ss.created_at,
               s.source_name, s.source_type, s.root_domain, s.official_flag
        FROM source_snapshot ss
        JOIN source s ON ss.source_id = s.id
        WHERE ss.company_id = %s
        ORDER BY ss.id DESC
        LIMIT 30
    """, (company_id,))
    snapshots = [
        {
            "id": r[0],
            "source_id": r[1],
            "company_id": r[2],
            "snapshot_type": r[3],
            "snapshot_title": r[4],
            "snapshot_url": r[5],
            "raw_storage_path": r[6],
            "parsed_text_storage_path": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
            "source_name": r[9],
            "source_type": r[10],
            "root_domain": r[11],
            "official_flag": r[12]
        }
        for r in cur.fetchall()
    ]

    cur.execute("""
        SELECT id, source_snapshot_id, company_id, evidence_type, evidence_title,
               evidence_text, evidence_number, evidence_unit, evidence_date, confidence_score
        FROM evidence_item
        WHERE company_id = %s
        ORDER BY id DESC
        LIMIT 40
    """, (company_id,))
    evidence_items = [
        {
            "id": r[0],
            "source_snapshot_id": r[1],
            "company_id": r[2],
            "evidence_type": r[3],
            "evidence_title": r[4],
            "evidence_text": r[5],
            "evidence_number": float(r[6]) if r[6] is not None else None,
            "evidence_unit": r[7],
            "evidence_date": r[8].isoformat() if r[8] else None,
            "confidence_score": float(r[9]) if r[9] is not None else None
        }
        for r in cur.fetchall()
    ]

    cur.execute("""
        SELECT id, company_id, metric_code, metric_name, metric_value, metric_unit,
               period_type, observation_date, source_snapshot_id, evidence_item_id
        FROM metric_observation
        WHERE company_id = %s
        ORDER BY id DESC
        LIMIT 40
    """, (company_id,))
    metrics = [
        {
            "id": r[0],
            "company_id": r[1],
            "metric_code": r[2],
            "metric_name": r[3],
            "metric_value": float(r[4]) if r[4] is not None else None,
            "metric_unit": r[5],
            "period_type": r[6],
            "observation_date": r[7].isoformat() if r[7] else None,
            "source_snapshot_id": r[8],
            "evidence_item_id": r[9]
        }
        for r in cur.fetchall()
    ]

    cur.execute("""
        SELECT cl.id, cl.request_id, cl.report_id, cl.claim_code, cl.evidence_item_id,
               cl.source_snapshot_id, cl.source_id, cl.citation_label, cl.citation_url, cl.citation_note
        FROM citation_link cl
        JOIN evidence_item ei ON cl.evidence_item_id = ei.id
        WHERE ei.company_id = %s
        ORDER BY cl.id DESC
        LIMIT 60
    """, (company_id,))
    citations = [
        {
            "id": r[0],
            "request_id": r[1],
            "report_id": r[2],
            "claim_code": r[3],
            "evidence_item_id": r[4],
            "source_snapshot_id": r[5],
            "source_id": r[6],
            "citation_label": r[7],
            "citation_url": r[8],
            "citation_note": r[9]
        }
        for r in cur.fetchall()
    ]

    return {
        "analysis_runs": analysis_runs,
        "recent_snapshots": snapshots,
        "recent_evidence_items": evidence_items,
        "recent_metric_observations": metrics,
        "recent_citations": citations
    }

def build_entity_summary(entity: dict, db_view: dict):
    return {
        "entity_name": entity.get("name"),
        "domain": entity.get("domain"),
        "analysis_run_count_recent": len(db_view.get("analysis_runs") or []),
        "source_snapshot_count_recent": len(db_view.get("recent_snapshots") or []),
        "evidence_item_count_recent": len(db_view.get("recent_evidence_items") or []),
        "metric_observation_count_recent": len(db_view.get("recent_metric_observations") or []),
        "citation_count_recent": len(db_view.get("recent_citations") or []),
        "signal_strength": (
            len(db_view.get("recent_evidence_items") or []) +
            len(db_view.get("recent_metric_observations") or []) +
            len(db_view.get("recent_citations") or [])
        ),
        "sample_evidence_titles": [x.get("evidence_title") for x in (db_view.get("recent_evidence_items") or [])[:6]],
        "sample_metric_codes": [x.get("metric_code") for x in (db_view.get("recent_metric_observations") or [])[:6]]
    }

def customer_recommendations(customer_name: str):
    if customer_name == "引望":
        return [
            "联合主张：Akkodis 的 SDV/验证交付能力 + Huawei Cloud/引望的 ADS/车云/鸿蒙座舱能力，形成面向全球 OEM 的平台型联合方案。",
            "优先场景：智能驾驶验证提效、车云闭环、全球本地化交付、海外认证与工程落地。",
            "差异化方向：把中国领先的智能汽车平台能力，与欧洲本地工程与客户覆盖能力组合起来。"
        ]
    if customer_name == "北汽":
        return [
            "联合主张：Akkodis 提供欧洲工程与交付能力，Huawei Cloud 提供 AI/MLOps/车云底座，帮助北汽加快智能化与出海运营。",
            "优先场景：OTA 质量闭环、智能座舱体验优化、远程诊断、海外车型适配和运营支撑。",
            "差异化方向：从“车型功能交付”升级到“车云一体持续运营能力”。"
        ]
    return [
        "基于客户的智能化成熟度与出海目标，联合定义 AI 全栈能力包。",
        "优先从可量化 ROI 的质量闭环、工程效率和车云服务切入。"
    ]

def build_recommendation_framework(case: dict, partner_summary: dict, cloud_summary: dict, customer_summaries: list, competitor_matrix: list):
    recommendations = [
        {
            "recommendation_code": "joint_solution_fit",
            "title": "Akkodis + Huawei Cloud 联合能力主张",
            "points": [
                "Akkodis 负责工程交付、验证、客户现场与欧洲本地化能力。",
                "Huawei Cloud 负责 AI 底座、ModelArts/MLOps、云边协同、车云能力。",
                "联合价值定位为：SDV 工程与验证工厂、OTA/质量闭环、海外合规与本地交付增强。"
            ]
        }
    ]

    for customer in customer_summaries:
        recommendations.append({
            "recommendation_code": f"customer-{slugify(customer.get('entity_name'))}",
            "title": f"{customer.get('entity_name')} 差异化联合方案",
            "points": customer_recommendations(customer.get("entity_name"))
        })

    recommendations.append({
        "recommendation_code": "benchmark_readout",
        "title": "欧洲竞争对手对标解读",
        "points": [
            "当前 benchmark 先以 evidence/metric/citation 信号强度作为早期可审计对比底座。",
            "后续再叠加更细的 metric normalization、维度权重与评分规则。",
            "优先观察 AI 能力、汽车垂直深度、工程交付与生态覆盖四类证据。"
        ],
        "competitor_signal_matrix": competitor_matrix
    })

    return recommendations

def write_output_file(case_code: str, data: dict):
    out_dir = ROOT / "outputs" / "account_strategy" / slugify(case_code) / ts_compact()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "account_strategy_case.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = skill_cfg()
    case = normalize_case(json.loads(args.input_json))

    partner = case["partner"]
    cloud_vendor = case["cloud_vendor"]
    customers = case["customers"]

    ingest_entities = [partner, cloud_vendor] + customers
    ingest_results = []

    for entity in ingest_entities:
        payload = build_ingest_payload(entity)
        result = run_runner(OFFICIAL_INGEST_RUNNER, payload, dry_run=args.dry_run)
        ingest_results.append({
            "entity_name": entity.get("name"),
            "entity_role": entity.get("role") or entity.get("type") or "entity",
            "ok": result.get("ok"),
            "ingest_payload": payload,
            "ingest_result": result.get("data") if result.get("ok") else None,
            "error": result.get("error")
        })

    competitor_result = None
    competitor_case_path = case.get("competitor_case_path")
    if competitor_case_path:
        competitor_payload = load_json(ROOT / competitor_case_path)
        competitor_result = run_runner(COMPETITOR_RUNNER, competitor_payload, dry_run=args.dry_run)

    db_views = {}
    entity_summaries = []

    if not args.dry_run:
        conn = db_connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SET search_path TO insight,public;")
                    for entity in ingest_entities:
                        company = fetch_company_by_domain_or_name(cur, entity.get("name"), entity.get("domain"))
                        if not company:
                            db_views[entity.get("name")] = {
                                "company": None,
                                "analysis_runs": [],
                                "recent_snapshots": [],
                                "recent_evidence_items": [],
                                "recent_metric_observations": [],
                                "recent_citations": []
                            }
                            entity_summaries.append({
                                "entity_name": entity.get("name"),
                                "domain": entity.get("domain"),
                                "analysis_run_count_recent": 0,
                                "source_snapshot_count_recent": 0,
                                "evidence_item_count_recent": 0,
                                "metric_observation_count_recent": 0,
                                "citation_count_recent": 0,
                                "signal_strength": 0,
                                "sample_evidence_titles": [],
                                "sample_metric_codes": []
                            })
                            continue

                        view = fetch_entity_db_view(cur, company["id"])
                        view["company"] = company
                        db_views[entity.get("name")] = view
                        entity_summaries.append(build_entity_summary(entity, view))
        finally:
            conn.close()
    else:
        for entity in ingest_entities:
            db_views[entity.get("name")] = {
                "company": None,
                "analysis_runs": [],
                "recent_snapshots": [],
                "recent_evidence_items": [],
                "recent_metric_observations": [],
                "recent_citations": []
            }
            entity_summaries.append({
                "entity_name": entity.get("name"),
                "domain": entity.get("domain"),
                "analysis_run_count_recent": 0,
                "source_snapshot_count_recent": 0,
                "evidence_item_count_recent": 0,
                "metric_observation_count_recent": 0,
                "citation_count_recent": 0,
                "signal_strength": 0,
                "sample_evidence_titles": [],
                "sample_metric_codes": []
            })

    summary_by_name = {x["entity_name"]: x for x in entity_summaries}
    partner_summary = summary_by_name.get(partner.get("name"), {})
    cloud_summary = summary_by_name.get(cloud_vendor.get("name"), {})
    customer_summaries = [summary_by_name.get(x.get("name"), {"entity_name": x.get("name")}) for x in customers]

    competitor_matrix = []
    competitor_db = {}
    if competitor_result and competitor_result.get("ok"):
        competitor_data = competitor_result.get("data") or {}
        competitor_matrix = competitor_data.get("comparison_matrix") or []
        competitor_db = competitor_data.get("db_backed_benchmark") or {}

    out = {
        "ok": True,
        "skill_name": "account_strategy_skill",
        "status": cfg.get("status", "scaffold"),
        "schema_version": "v1",
        "ts": utc_now(),
        "dry_run": bool(args.dry_run),
        "skill_config": cfg,
        "request": case,
        "conclusion": "account_strategy_skill now orchestrates real entity ingestion and competitor benchmark execution, producing a DB-backed account-strategy synthesis input for downstream business artifacts.",
        "core_data": [
            {"field": "case_code", "value": case.get("case_code")},
            {"field": "partner_name", "value": partner.get("name")},
            {"field": "cloud_vendor_name", "value": cloud_vendor.get("name")},
            {"field": "customer_count", "value": len(customers)},
            {"field": "official_ingest_entity_count", "value": len(ingest_entities)},
            {"field": "official_ingest_success_count", "value": sum(1 for x in ingest_results if x.get("ok"))},
            {"field": "competitor_case_attached", "value": bool(competitor_case_path)}
        ],
        "sources": [
            {"entity_name": x["entity_name"], "entity_role": x["entity_role"], "sources": x["ingest_payload"].get("sources") or []}
            for x in ingest_results
        ],
        "facts": [
            "This skill now executes real official-source ingestion for partner/cloud/customer entities.",
            "It also consumes real competitor benchmark output from competitor_research_skill."
        ],
        "inferences": [
            "The account-strategy layer can now synthesize cross-entity evidence instead of relying on manual narrative assembly."
        ],
        "hypotheses": [
            "The strongest business differentiation should come from combining European engineering delivery with Huawei Cloud/引望智能汽车平台能力 and customer-specific rollout design."
        ],
        "risks": [
            "Current recommendation logic is still rule-based and should later be replaced with evidence-weighted synthesis.",
            "Formal Word/Excel/PPT generation still needs report_build_skill to consume this account-strategy output."
        ],
        "next_steps": [
            "Make report_build_skill consume account-strategy JSON + citation_link.",
            "Generate Word / Excel / PPT artifacts for this case.",
            "Register artifacts and deliver them through Feishu."
        ],
        "official_ingest_results": ingest_results,
        "entity_summaries": entity_summaries,
        "partner_summary": partner_summary,
        "cloud_vendor_summary": cloud_summary,
        "customer_summaries": customer_summaries,
        "competitor_benchmark_ref": {
            "case_path": competitor_case_path,
            "ok": competitor_result.get("ok") if competitor_result else False,
            "comparison_matrix": competitor_matrix
        },
        "recommendation_framework": build_recommendation_framework(
            case,
            partner_summary,
            cloud_summary,
            customer_summaries,
            competitor_matrix
        ),
        "db_backed_entities": db_views,
        "db_backed_competitors": competitor_db,
        "db_write_plan": cfg.get("db_write_intent", []),
        "artifact_plan": [
            {"artifact_type": "word", "template_code": "enterprise_report_v1"},
            {"artifact_type": "excel", "template_code": "evidence_matrix_v1"},
            {"artifact_type": "ppt", "template_code": "executive_briefing_v1"}
        ]
    }

    out["output_json_path"] = write_output_file(case["case_code"], out)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
