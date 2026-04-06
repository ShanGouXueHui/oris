#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = ROOT / "config" / "insight_skill_runtime.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_runtime():
    if not RUNTIME_PATH.is_file():
        return {}
    return json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))

def skill_cfg(skill_name):
    return ((load_runtime().get("skills") or {}).get(skill_name)) or {}

def load_request(input_file=None, input_json=None, default=None):
    if input_file:
        return json.loads(Path(input_file).read_text(encoding="utf-8"))
    if input_json:
        return json.loads(input_json)
    return default or {}

def build_standard_output(
    skill_name,
    request,
    conclusion,
    core_data=None,
    sources=None,
    facts=None,
    inferences=None,
    hypotheses=None,
    risks=None,
    next_steps=None,
    source_plan=None,
    db_write_plan=None,
    artifact_plan=None,
):
    runtime = load_runtime()
    return {
        "ok": True,
        "skill_name": skill_name,
        "status": "scaffold",
        "schema_version": runtime.get("default_output_schema_version", "v1"),
        "ts": utc_now(),
        "skill_config": skill_cfg(skill_name),
        "request": request,
        "conclusion": conclusion,
        "core_data": core_data or [],
        "sources": sources or [],
        "facts": facts or [],
        "inferences": inferences or [],
        "hypotheses": hypotheses or [],
        "risks": risks or [],
        "next_steps": next_steps or [],
        "source_plan": source_plan or [],
        "db_write_plan": db_write_plan or [],
        "artifact_plan": artifact_plan or [],
    }
