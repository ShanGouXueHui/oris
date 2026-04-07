#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "scripts" / "prompt_to_case_compiler_plus_v2.py"

GENERIC_CUSTOMER_NAME = "generic_automotive_customer"
GENERIC_CUSTOMER_DISPLAY = "通用车企客户（未指定）"

GENERIC_SEGMENTS = [
    "Top主机厂",
    "国央企车企",
    "新势力车企",
    "Tier1/智驾平台客户"
]

GENERIC_QUESTIONS = [
    "若未指定具体客户，哪些通用汽车客户场景最适合切入？",
    "针对主机厂、Tier1、智驾平台三类客户，联合打法应如何区分？",
    "在未指定客户时，最容易先落地的 PoC 场景是什么？",
    "若从通用汽车客户拓展视角出发，最关键的差异化卖点是什么？"
]

GENERIC_REPORT_SECTIONS = [
    "company_or_case_overview",
    "industry_and_competition",
    "technology_stack_breakdown",
    "generic_customer_segmentation",
    "customer_scenario_analysis",
    "recommendations",
    "risks",
    "citations_appendix"
]

GENERIC_PPT_SECTIONS = [
    "title",
    "executive_summary",
    "industry_context",
    "competitive_position",
    "technology_stack",
    "generic_customer_segments",
    "customer_scenarios",
    "recommendations",
    "risks"
]

def parse_json_text(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        pass
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(s[start:end+1])
        except Exception:
            return None
    return None

def run_json(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "").strip()[:4000])
    obj = parse_json_text(r.stdout)
    if obj is None:
        raise RuntimeError("upstream stdout is not valid json")
    return obj

def uniq_keep_order(items):
    seen = set()
    out = []
    for x in items or []:
        if not x:
            continue
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out

def contains_any(text: str, words):
    s = (text or "").lower()
    return any(w.lower() in s for w in words)

def infer_chat_md(prompt_text: str):
    return contains_any(prompt_text, [
        "直接回复飞书聊天内容",
        "适合手机直接阅读",
        "手机直接阅读",
        "聊天内容",
        "md",
        "markdown",
        "不要ppt",
        "不要word",
        "不生成附件",
        "直接回复"
    ])

def infer_generic_automotive_customer(prompt_text: str):
    return contains_any(prompt_text, [
        "汽车行业", "车企", "主机厂", "tier1", "tier-1", "tier 1",
        "智驾", "智能驾驶", "座舱", "汽车客户", "整车厂"
    ])

def normalize_case(compiled_case: dict, prompt_text: str):
    if not isinstance(compiled_case, dict):
        return compiled_case

    role_bindings = compiled_case.setdefault("role_bindings", {})
    profile_code = compiled_case.get("profile_code")
    analysis_type = compiled_case.get("analysis_type")

    if infer_chat_md(prompt_text):
        compiled_case["delivery_mode"] = "chat_md"
        compiled_case["deliverables"] = ["chat_md"]

    # 核心泛化逻辑：partner + cloud_vendor 存在时，不再要求具体客户名
    if profile_code == "account_strategy_partner_cloud_customer" or analysis_type == "account_strategy":
        partner = role_bindings.get("partner")
        cloud_vendor = role_bindings.get("cloud_vendor")
        target_customer = role_bindings.get("target_customer")

        if partner and cloud_vendor and (not target_customer) and infer_generic_automotive_customer(prompt_text):
            region = (
                (partner.get("region") if isinstance(partner, dict) else None)
                or (cloud_vendor.get("region") if isinstance(cloud_vendor, dict) else None)
                or "CN"
            )

            role_bindings["target_customer"] = {
                "name": GENERIC_CUSTOMER_NAME,
                "display_name": GENERIC_CUSTOMER_DISPLAY,
                "region": region,
                "type": "customer",
                "placeholder": True,
                "industry": "automotive",
                "sources": []
            }

            compiled_case["generic_customer_mode"] = True
            compiled_case["customer_scope"] = "generic_oem_tier1"
            compiled_case["customer_segments"] = GENERIC_SEGMENTS

            compiled_case["questions"] = uniq_keep_order(
                (compiled_case.get("questions") or []) + GENERIC_QUESTIONS
            )
            compiled_case["report_sections"] = uniq_keep_order(
                (compiled_case.get("report_sections") or []) + GENERIC_REPORT_SECTIONS
            )
            compiled_case["ppt_sections"] = uniq_keep_order(
                (compiled_case.get("ppt_sections") or []) + GENERIC_PPT_SECTIONS
            )

            trace = compiled_case.setdefault("trace_tail", [])
            trace.append("generic_customer_fallback")

    return compiled_case

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-text")
    ap.add_argument("--write-output", action="store_true")
    args = ap.parse_args()

    if not args.prompt_text:
        raise SystemExit("missing --prompt-text")

    cmd = [sys.executable, str(UPSTREAM), "--prompt-text", args.prompt_text]
    if args.write_output:
        cmd.append("--write-output")

    compiled_case = run_json(cmd)
    compiled_case = normalize_case(compiled_case, args.prompt_text)

    out_path = compiled_case.get("compiled_case_path")
    if args.write_output and out_path:
        p = Path(out_path)
        if not p.is_absolute():
            p = ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(compiled_case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(compiled_case, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
