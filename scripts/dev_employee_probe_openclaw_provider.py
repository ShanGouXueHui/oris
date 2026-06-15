#!/usr/bin/env python3
"""Run one safe, non-task OpenClaw Gateway inference contract probe.

The probe performs no queue mutation and no product change. It asks the real
OpenClaw infer Gateway path to classify a synthetic engineering request and
writes only sanitized contract metadata and the structured routing result.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dev_employee_openclaw_provider import OpenClawInferCLIProvider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--binary", default="/home/admin/.npm-global/bin/openclaw")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    projects = {
        "oris-final-acceptance-api": {
            "name": "ORIS Final Acceptance API",
            "type": "test_project",
            "notes": "Standalone test API project.",
            "allowed_scope": ["README.md", "AGENTS.md", "docs/", "app/", "tests/", "requirements.txt", ".gitignore"],
            "forbidden_scope": [".env", "secrets", "private_keys", "production_credentials"],
        },
        "oris": {
            "name": "ORIS",
            "type": "platform",
            "notes": "AI employee platform and orchestration repository.",
            "allowed_scope": ["docs/", "orchestration/", "scripts/", "logs/dev_employee/", "memory/"],
            "forbidden_scope": [".env", "secrets", "production_credentials"],
        },
    }
    session = {
        "session_id": "chat-provider-contract-probe",
        "locale": "zh-CN",
        "selected_project": None,
        "current_task_id": None,
        "messages": [
            {
                "role": "assistant",
                "content": "你好，我是 ORIS AI 开发员工。",
            }
        ],
    }
    message = "请在 ORIS Final Acceptance API 项目增加一个只读 /healthz 接口，并完成相应测试。"
    provider = OpenClawInferCLIProvider(
        Path(args.binary),
        timeout=max(10, min(180, args.timeout)),
        thinking="low",
        require_gateway=True,
    )
    result = provider.analyze(
        session=session,
        user_message=message,
        projects=projects,
        current_task=None,
    )
    if result.provider != "openclaw_infer_gateway":
        raise RuntimeError(f"unexpected provider: {result.provider}")
    if result.intent != "create_task":
        raise RuntimeError(f"unexpected intent: {result.intent}")
    if result.project_key != "oris-final-acceptance-api":
        raise RuntimeError(f"unexpected project: {result.project_key}")
    if not result.objective or "/healthz" not in result.objective:
        raise RuntimeError("objective does not preserve /healthz")
    if result.requires_confirmation:
        raise RuntimeError("safe synthetic request unexpectedly requires confirmation")

    output = {
        "result": "PASS",
        "provider": result.provider,
        "intent": result.intent,
        "project_key": result.project_key,
        "objective_contains_healthz": "/healthz" in (result.objective or ""),
        "assistant_message_present": bool(result.assistant_message),
        "constraint_count": len(result.constraints),
        "expected_check_count": len(result.expected_checks),
        "requires_confirmation": result.requires_confirmation,
        "transport": result.raw_metadata.get("transport"),
        "model_provider": result.raw_metadata.get("provider"),
        "model": result.raw_metadata.get("model"),
        "capability": result.raw_metadata.get("capability"),
        "openclaw_binary": result.raw_metadata.get("openclaw_binary"),
        "real_product_task_submitted": False,
        "product_changed": False,
        "secrets_logged": False,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
