#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPILER = ROOT / "scripts" / "prompt_to_case_compiler.py"
RUNTIME_CFG_PATH = ROOT / "config" / "insight_skill_runtime.json"

def resolve_compiler():
    cfg = load_json(RUNTIME_CFG_PATH)
    rel = ((cfg.get("generic_runtime") or {}).get("prompt_compiler_script") or "scripts/prompt_to_case_compiler.py")
    return ROOT / rel
PROFILES_PATH = ROOT / "config" / "insight_case_profiles.json"

def ts_compact():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def run_json(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "").strip()[:4000])
    try:
        return json.loads(r.stdout)
    except Exception as e:
        raise RuntimeError(f"non_json_output: {e}\n{r.stdout[:2000]}")

def relpath(path: Path):
    return str(path.relative_to(ROOT))

def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def run_delivery_for_prefix(report_prefix: str):
    register_out = run_json([
        "/usr/bin/python3",
        str(ROOT / "scripts" / "register_report_build_delivery.py")
    ])
    matched = [
        x for x in (register_out.get("files") or [])
        if report_prefix and report_prefix in (x.get("path") or "")
    ]

    delivery_r = subprocess.run(
        ["/usr/bin/python3", str(ROOT / "scripts" / "delivery_executor.py"), "--once", "--max-tasks", "40"],
        capture_output=True, text=True, check=False
    )

    return {
        "registered_files": matched,
        "delivery_executor_rc": delivery_r.returncode,
        "delivery_executor_stdout_tail": (delivery_r.stdout or "")[-5000:],
        "delivery_executor_stderr_tail": (delivery_r.stderr or "")[-2000:]
    }

def run_account_strategy_profile(compiled_case: dict, profiles_cfg: dict, skip_register_delivery: bool = False):
    profile = (profiles_cfg.get("profiles") or {}).get("account_strategy_partner_cloud_customer") or {}
    downstream = profile.get("downstream") or {}

    bindings = compiled_case.get("role_bindings") or {}
    partner = bindings.get("partner")
    cloud_vendor = bindings.get("cloud_vendor")
    customers = bindings.get("customers") or []
    competitors = bindings.get("competitors") or []

    if not partner or not cloud_vendor:
        raise RuntimeError("account_strategy profile requires detected partner and cloud_vendor")

    base_dir = ROOT / "inputs" / "generated_cases" / compiled_case["case_code"] / ts_compact()
    base_dir.mkdir(parents=True, exist_ok=True)

    competitor_case = {
        "case_code": f"competitor-{compiled_case['case_code']}",
        "analysis_type": "competitor_research",
        "target_company": {
            "name": partner.get("name"),
            "domain": partner.get("domain"),
            "region": partner.get("region"),
            "sources": partner.get("sources") or []
        },
        "competitors": [
            {
                "name": x.get("name"),
                "domain": x.get("domain"),
                "region": x.get("region"),
                "sources": x.get("sources") or []
            }
            for x in competitors
        ],
        "dimensions": compiled_case.get("dimensions") or profile.get("default_dimensions") or [],
        "required_artifacts": compiled_case.get("deliverables") or ["word", "excel", "ppt"]
    }
    competitor_case_path = base_dir / "competitor_case.json"
    write_json(competitor_case_path, competitor_case)

    account_case = {
        "case_code": compiled_case["case_code"],
        "analysis_type": "account_strategy",
        "partner": {
            "name": partner.get("name"),
            "domain": partner.get("domain"),
            "region": partner.get("region"),
            "role": "solution_partner",
            "sources": partner.get("sources") or []
        },
        "cloud_vendor": {
            "name": cloud_vendor.get("name"),
            "domain": cloud_vendor.get("domain"),
            "region": cloud_vendor.get("region"),
            "role": "ai_cloud_platform",
            "sources": cloud_vendor.get("sources") or []
        },
        "customers": [
            {
                "name": x.get("name"),
                "domain": x.get("domain"),
                "region": x.get("region"),
                "type": "customer",
                "sources": x.get("sources") or []
            }
            for x in customers
        ],
        "competitor_case_path": relpath(competitor_case_path),
        "dimensions": compiled_case.get("dimensions") or profile.get("default_dimensions") or [],
        "questions": compiled_case.get("questions") or [],
        "required_artifacts": compiled_case.get("deliverables") or ["word", "excel", "ppt"],
        "compiled_case_path": compiled_case.get("compiled_case_path"),
        "methodology_profile": compiled_case.get("methodology_profile"),
        "frameworks": compiled_case.get("frameworks") or [],
        "report_sections": compiled_case.get("report_sections") or [],
        "ppt_sections": compiled_case.get("ppt_sections") or [],
        "freshness_policy": {
            "same_day_required": True,
            "force_refresh_on_new_prompt": True
        },
        "force_refresh": True
    }
    account_case_path = base_dir / "account_strategy_case_input.json"
    write_json(account_case_path, account_case)

    account_out = run_json([
        "/usr/bin/python3",
        str(ROOT / downstream["account_strategy_runner"]),
        "--input-json",
        json.dumps(account_case, ensure_ascii=False)
    ])

    report_req = {
        "analysis_type": "account_strategy",
        "input_json_path": account_out["output_json_path"],
        "artifact_types": compiled_case.get("deliverables") or ["word", "excel", "ppt"]
    }

    report_out = run_json([
        "/usr/bin/python3",
        str(ROOT / downstream["report_runner"]),
        "--input-json",
        json.dumps(report_req, ensure_ascii=False)
    ])

    artifact_plan = report_out.get("artifact_plan") or []
    downloadable_types = {"word", "excel", "ppt"}
    filtered_artifact_plan = [x for x in artifact_plan if x.get("artifact_type") in downloadable_types]
    artifact_paths = [x["path"] for x in filtered_artifact_plan]
    postprocess_out = run_evolution_postprocess(
        "account_strategy",
        account_out.get("output_json_path"),
        compiled_case.get("compiled_case_path"),
        artifact_paths
    )
    report_prefix = str(Path(artifact_paths[0]).parent) if artifact_paths else ""
    if skip_register_delivery:
        delivery_info = {
            "registered_files": [],
            "delivery_executor_rc": None,
            "delivery_executor_stdout_tail": "",
            "delivery_executor_stderr_tail": ""
        }
    else:
        delivery_info = run_delivery_for_prefix(report_prefix)

    return {
        "compiled_case_path": compiled_case.get("compiled_case_path"),
        "compiler_parser_mode": compiled_case.get("parser_mode"),
        "compiler_execution_mode": compiled_case.get("execution_mode"),
        "compiler_llm_compare_mode": ((compiled_case.get("llm_compare") or {}).get("mode")),
        "compiler_compare_summary": compiled_case.get("compare_summary"),
        "external_skill_candidates": compiled_case.get("external_skill_candidates") or [],
        "evolution_actions": compiled_case.get("evolution_actions") or [],
        "generated_case_paths": {
            "competitor_case_path": relpath(competitor_case_path),
            "account_case_path": relpath(account_case_path)
        },
        "account_strategy_output_json": account_out.get("output_json_path"),
        "report_build_artifacts": filtered_artifact_plan,
        "evolution_postprocess": postprocess_out,
        **delivery_info
    }


def run_evolution_postprocess(analysis_type: str, source_json_path: str, compiled_case_path: str, artifact_paths: list[str]):
    if not artifact_paths:
        return {"ok": False, "reason": "no_artifacts"}
    report_dir = str(Path(artifact_paths[0]).parent)
    r = subprocess.run(
        [
            "/usr/bin/python3",
            str(ROOT / "skills" / "report_build_skill" / "evolution_postprocess.py"),
            "--analysis-type", analysis_type,
            "--source-json-path", source_json_path,
            "--compiled-case-path", compiled_case_path,
            "--report-build-dir", report_dir
        ],
        capture_output=True, text=True, check=False
    )
    if r.returncode != 0:
        return {
            "ok": False,
            "returncode": r.returncode,
            "stdout_tail": (r.stdout or "")[-2000:],
            "stderr_tail": (r.stderr or "")[-2000:]
        }
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"ok": True, "stdout_tail": (r.stdout or "")[-2000:]}

def run_company_profile_profile(compiled_case: dict, profiles_cfg: dict, skip_register_delivery: bool = False):
    profile = (profiles_cfg.get("profiles") or {}).get("company_profile") or {}
    downstream = profile.get("downstream") or {}

    bindings = compiled_case.get("role_bindings") or {}
    target = bindings.get("target_company")
    if not target:
        raise RuntimeError("company_profile profile requires detected target_company")

    base_dir = ROOT / "inputs" / "generated_cases" / compiled_case["case_code"] / ts_compact()
    base_dir.mkdir(parents=True, exist_ok=True)

    ingest_payload = {
        "entity": target.get("name"),
        "domain": target.get("domain"),
        "region": target.get("region"),
        "time_range": "latest",
        "sources": target.get("sources") or []
    }

    ingest_out = run_json([
        "/usr/bin/python3",
        str(ROOT / "skills" / "official_source_ingest_skill" / "runner.py"),
        "--input-json",
        json.dumps(ingest_payload, ensure_ascii=False)
    ])

    profile_req = {
        "company_name": target.get("name"),
        "domain": target.get("domain"),
        "region": target.get("region"),
        "freshness_policy": {
            "same_day_required": True,
            "force_refresh_on_new_prompt": True
        },
        "force_refresh": True
    }

    profile_out = run_json([
        "/usr/bin/python3",
        str(ROOT / downstream["company_profile_runner"]),
        "--input-json",
        json.dumps(profile_req, ensure_ascii=False)
    ])

    profile_out_path = base_dir / "company_profile_output.json"
    write_json(profile_out_path, profile_out)

    bundle_out = run_json([
        "/usr/bin/python3",
        str(ROOT / downstream["bundle_runner"]),
        "--input-json-path",
        str(profile_out_path)
    ])

    artifact_plan = bundle_out.get("artifact_plan") or []
    downloadable_types = {"word", "excel", "ppt"}
    filtered_artifact_plan = [x for x in artifact_plan if x.get("artifact_type") in downloadable_types]
    artifact_paths = [x["path"] for x in filtered_artifact_plan]
    postprocess_out = run_evolution_postprocess(
        "company_profile",
        str(profile_out_path),
        compiled_case.get("compiled_case_path"),
        artifact_paths
    )
    report_prefix = str(Path(artifact_paths[0]).parent) if artifact_paths else ""
    if skip_register_delivery:
        delivery_info = {
            "registered_files": [],
            "delivery_executor_rc": None,
            "delivery_executor_stdout_tail": "",
            "delivery_executor_stderr_tail": ""
        }
    else:
        delivery_info = run_delivery_for_prefix(report_prefix)

    return {
        "compiled_case_path": compiled_case.get("compiled_case_path"),
        "compiler_parser_mode": compiled_case.get("parser_mode"),
        "compiler_execution_mode": compiled_case.get("execution_mode"),
        "compiler_llm_compare_mode": ((compiled_case.get("llm_compare") or {}).get("mode")),
        "compiler_compare_summary": compiled_case.get("compare_summary"),
        "external_skill_candidates": compiled_case.get("external_skill_candidates") or [],
        "evolution_actions": compiled_case.get("evolution_actions") or [],
        "generated_case_paths": {
            "company_profile_output_path": relpath(profile_out_path)
        },
        "official_ingest_summary": {
            "conclusion": ingest_out.get("conclusion"),
            "core_data": ingest_out.get("core_data")
        },
        "company_profile_artifacts": filtered_artifact_plan,
        "evolution_postprocess": postprocess_out,
        **delivery_info
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-text")
    ap.add_argument("--enable-register-delivery", action="store_true")
    ap.add_argument("--compiled-case-path")
    args = ap.parse_args()

    profiles_cfg = load_json(PROFILES_PATH)

    if args.compiled_case_path:
        compiled_case = load_json(ROOT / args.compiled_case_path)
    elif args.prompt_text:
        compiled_case = run_json([
            "/usr/bin/python3",
            str(resolve_compiler()),
            "--prompt-text",
            args.prompt_text,
            "--write-output"
        ])
    else:
        raise SystemExit("must provide --prompt-text or --compiled-case-path")

    profile_code = compiled_case.get("profile_code")

    if profile_code == "account_strategy_partner_cloud_customer":
        payload = run_account_strategy_profile(
            compiled_case,
            profiles_cfg,
            skip_register_delivery=(not args.enable_register_delivery)
        )
    elif profile_code == "company_profile":
        payload = run_company_profile_profile(
            compiled_case,
            profiles_cfg,
            skip_register_delivery=(not args.enable_register_delivery)
        )
    else:
        raise RuntimeError(f"unsupported profile for generic pipeline today: {profile_code}")

    out = {
        "ok": True,
        "schema_version": "v1",
        "profile_code": profile_code,
        "case_code": compiled_case.get("case_code"),
        "analysis_type": compiled_case.get("analysis_type"),
        "deliverables": compiled_case.get("deliverables") or [],
        "payload": payload
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
