#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INNER = ROOT / "scripts" / "run_generic_insight_pipeline.py"
COMPILER = ROOT / "scripts" / "prompt_to_case_compiler_plus_v3.py"
RENDER = ROOT / "scripts" / "render_chat_md_from_bundle.py"
ACCOUNT_CHAT_RENDER = ROOT / "scripts" / "render_account_strategy_chat_md.py"
SEND = ROOT / "scripts" / "send_feishu_text_message.py"
REGISTER = ROOT / "scripts" / "register_report_build_delivery.py"
EXECUTOR = ROOT / "scripts" / "delivery_executor.py"

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
        return json.loads(s[start:end+1])
    return None

def run_json(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "").strip()[:4000])
    obj = parse_json_text(r.stdout)
    if obj is None:
        raise RuntimeError("stdout is not valid json")
    return obj

def relpath(p: str):
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except Exception:
        return p

def run_delivery_for_prefix(prefix: str):
    matched = run_json([
        sys.executable,
        str(REGISTER),
        "--report-prefix",
        prefix
    ])
    r = subprocess.run(
        [sys.executable, str(EXECUTOR), "--once", "--max-tasks", "40"],
        capture_output=True, text=True, check=False
    )
    return {
        "registered_files": matched.get("files") or [],
        "registered_count": len(matched.get("files") or []),
        "delivery_executor_rc": r.returncode,
        "delivery_executor_stdout_tail": (r.stdout or "")[-5000:],
        "delivery_executor_stderr_tail": (r.stderr or "")[-2000:]
    }

def extract_artifacts(payload: dict):
    items = payload.get("report_build_artifacts") or payload.get("company_profile_artifacts") or []
    return [x for x in items if isinstance(x, dict)]

def find_bundle_path(artifacts: list[dict]):
    for x in artifacts:
        p = x.get("path") or ""
        if p.endswith("_bundle.json"):
            return p
    return ""

def extract_artifact_paths_from_payload(payload: dict) -> list[str]:
    paths = []
    for key in ("internal_report_build_artifacts", "report_build_artifacts", "company_profile_artifacts"):
        for item in (payload.get(key) or []):
            if isinstance(item, dict):
                v = item.get("path")
                if isinstance(v, str) and v.strip():
                    paths.append(v.strip())
    return paths

def resolve_bundle_json_path(payload: dict, artifact_paths: list[str]) -> str:
    candidates: list[Path] = []

    def add_candidate(v):
        if not isinstance(v, str):
            return
        raw = v.strip()
        if not raw or raw == ".":
            return
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        candidates.append(path)

    for key in (
        "bundle_json_path",
        "report_bundle_path",
        "company_profile_bundle_path",
        "chat_reply_bundle_path",
    ):
        add_candidate(payload.get(key))

    for key in (
        "internal_report_build_artifacts",
        "report_build_artifacts",
        "internal_company_profile_artifacts",
        "company_profile_artifacts",
    ):
        for item in (payload.get(key) or []):
            if isinstance(item, dict):
                add_candidate(item.get("path"))

    for ap in (artifact_paths or []):
        add_candidate(ap)
        raw = Path(ap)
        parent = raw if raw.is_dir() else raw.parent
        if not parent.is_absolute():
            parent = ROOT / parent
        if parent.exists() and parent.is_dir():
            for m in sorted(parent.glob("*_bundle.json")):
                candidates.append(m)

    seen = set()
    normalized = []
    for c in candidates:
        try:
            key = str(c.resolve())
        except Exception:
            key = str(c)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(c)

    for c in normalized:
        if c.exists() and c.is_file() and c.name.endswith("_bundle.json"):
            try:
                return str(c.resolve().relative_to(ROOT))
            except Exception:
                return str(c.resolve())

    debug = {
        "artifact_paths": artifact_paths,
        "payload_keys": sorted(list(payload.keys())),
    }
    raise RuntimeError(f"bundle json path not found; debug={debug}")

def build_blocked_result(compiled_case: dict):
    precheck = compiled_case.get("precheck") or {}
    return {
        "ok": True,
        "blocked": True,
        "profile_code": compiled_case.get("profile_code"),
        "analysis_type": compiled_case.get("analysis_type"),
        "compiled_case_path": compiled_case.get("compiled_case_path"),
        "precheck": precheck,
        "payload": {
            "precheck": precheck,
            "chat_delivery_mode": "blocked",
            "chat_reply_path": "",
            "chat_reply_preview": "",
            "registered_files": [],
            "registered_count": 0,
            "delivery_executor_rc": None,
            "delivery_executor_stdout_tail": "",
            "delivery_executor_stderr_tail": ""
        }
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-text")
    ap.add_argument("--compiled-case-path")
    ap.add_argument("--enable-register-delivery", action="store_true")
    ap.add_argument("--chat-id")
    args = ap.parse_args()

    if args.compiled_case_path:
        compiled_case = json.loads((ROOT / args.compiled_case_path).read_text(encoding="utf-8"))
    elif args.prompt_text:
        compiled_case = run_json([
            sys.executable,
            str(COMPILER),
            "--prompt-text",
            args.prompt_text,
            "--write-output"
        ])
    else:
        raise SystemExit("must provide --prompt-text or --compiled-case-path")

    if compiled_case.get("blocked") or ((compiled_case.get("precheck") or {}).get("blocked")):
        print(json.dumps(build_blocked_result(compiled_case), ensure_ascii=False, indent=2))
        return

    inner = run_json([
        sys.executable,
        str(INNER),
        "--compiled-case-path",
        compiled_case["compiled_case_path"]
    ])

    payload = inner.get("payload") or {}
    artifacts = extract_artifacts(payload)
    bundle_path = find_bundle_path(artifacts)

    delivery_mode = compiled_case.get("delivery_mode") or "chat_md"
    profile_code = inner.get("profile_code")
    analysis_type = inner.get("analysis_type")

    if delivery_mode == "artifact_bundle":
        if artifacts:
            prefix = str(Path(artifacts[0]["path"]).parent)
        else:
            prefix = ""
        if args.enable_register_delivery and prefix:
            payload.update(run_delivery_for_prefix(prefix))
        else:
            payload.update({
                "registered_files": [],
                "registered_count": 0,
                "delivery_executor_rc": None,
                "delivery_executor_stdout_tail": "",
                "delivery_executor_stderr_tail": ""
            })
    else:
        artifact_paths = extract_artifact_paths_from_payload(payload)
        render_input_path = (
            payload.get("account_strategy_output_json")
            or payload.get("company_profile_output_json")
            or resolve_bundle_json_path(payload, artifact_paths)
        )
        if analysis_type == "account_strategy" and payload.get("account_strategy_output_json"):
            md_out = run_json([
                sys.executable,
                str(ACCOUNT_CHAT_RENDER),
                "--account-json-path",
                payload["account_strategy_output_json"],
                "--compiled-case-path",
                compiled_case["compiled_case_path"]
            ])
        else:
            md_out = run_json([
                sys.executable,
                str(RENDER),
                "--bundle-json-path",
                render_input_path,
                "--compiled-case-path",
                compiled_case["compiled_case_path"]
            ])
        chat_send = None
        send_rc = None

        if "report_build_artifacts" in payload:
            payload["internal_report_build_artifacts"] = payload.get("report_build_artifacts") or []
            payload["report_build_artifacts"] = []
        if "company_profile_artifacts" in payload:
            payload["internal_company_profile_artifacts"] = payload.get("company_profile_artifacts") or []
            payload["company_profile_artifacts"] = []

        payload.update({
            "chat_delivery_mode": "chat_md",
            "chat_reply_path": md_out.get("output_path"),
            "chat_reply_preview": md_out.get("preview"),
            "source_link_count": md_out.get("source_link_count"),
            "chat_send_result": chat_send,
            "registered_files": [],
            "registered_count": 0,
            "delivery_executor_rc": send_rc,
            "delivery_executor_stdout_tail": json.dumps(chat_send, ensure_ascii=False) if chat_send else "",
            "delivery_executor_stderr_tail": ""
        })

    out = {
        "ok": True,
        "schema_version": "v1",
        "profile_code": profile_code,
        "case_code": inner.get("case_code"),
        "analysis_type": analysis_type,
        "deliverables": compiled_case.get("deliverables") or [],
        "payload": payload
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
