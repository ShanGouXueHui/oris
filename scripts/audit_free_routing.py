#!/usr/bin/env python3
"""Audit ORIS free-model routing artifacts.

Checks that active routing and runtime plan stay on free candidates and do not
select mixed-cost router defaults for primary roles.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PATH = ROOT / "orchestration" / "active_routing.json"
RUNTIME_PLAN_PATH = ROOT / "orchestration" / "runtime_plan.json"
REPORT_JSON = ROOT / "logs" / "dev_employee" / "latest_free_routing_audit.json"
REPORT_MD = ROOT / "logs" / "dev_employee" / "latest_free_routing_audit.md"

FORBIDDEN_MODELS = {"openrouter/auto"}
REQUIRED_ROLES = ["primary_general", "free_fallback", "report_generation", "coding", "cn_candidate_pool"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    return raw if isinstance(raw, dict) else {}


def audit_active(active: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    decisions = active.get("decisions", {}) if isinstance(active.get("decisions"), dict) else {}
    for role in REQUIRED_ROLES:
        info = decisions.get(role, {}) if isinstance(decisions.get(role), dict) else {}
        selected = info.get("selected_model")
        free_candidate = info.get("free_candidate")
        ok = bool(selected) and selected not in FORBIDDEN_MODELS and free_candidate is True
        findings.append(
            {
                "artifact": "active_routing",
                "role": role,
                "ok": ok,
                "selected_model": selected,
                "free_candidate": free_candidate,
                "provider_id": info.get("provider_id"),
                "reason": "ok" if ok else "selected model is missing, forbidden, or not marked free",
            }
        )
    return findings


def audit_runtime_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    plans = plan.get("plans", {}) if isinstance(plan.get("plans"), dict) else {}
    for role in REQUIRED_ROLES:
        info = plans.get(role, {}) if isinstance(plans.get(role), dict) else {}
        primary = info.get("execution_primary")
        selected = info.get("selected_model")
        chain = info.get("failover_chain", []) if isinstance(info.get("failover_chain"), list) else []
        primary_meta = next((item for item in chain if isinstance(item, dict) and item.get("model_id") == primary), {})
        ok = bool(primary) and primary not in FORBIDDEN_MODELS and primary_meta.get("free_verified") is True
        findings.append(
            {
                "artifact": "runtime_plan",
                "role": role,
                "ok": ok,
                "selected_model": selected,
                "execution_primary": primary,
                "free_verified": primary_meta.get("free_verified"),
                "provider_id": primary_meta.get("provider_id"),
                "reason": "ok" if ok else "execution primary is missing, forbidden, or not free-verified",
            }
        )
    return findings


def write_reports(payload: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# ORIS Free Routing Audit",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- ok: `{payload['ok']}`",
        "",
        "| Artifact | Role | OK | Selected / Primary | Provider | Reason |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["findings"]:
        model = item.get("execution_primary") or item.get("selected_model")
        lines.append(
            f"| `{item.get('artifact')}` | `{item.get('role')}` | `{item.get('ok')}` | `{model}` | `{item.get('provider_id')}` | {item.get('reason')} |"
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    active = load_json(ACTIVE_PATH)
    plan = load_json(RUNTIME_PLAN_PATH)
    findings = audit_active(active) + audit_runtime_plan(plan)
    ok = all(item["ok"] for item in findings)
    payload = {
        "ok": ok,
        "generated_at": utc_now(),
        "forbidden_models": sorted(FORBIDDEN_MODELS),
        "findings": findings,
        "source_files": {
            "active_routing": str(ACTIVE_PATH),
            "runtime_plan": str(RUNTIME_PLAN_PATH),
        },
    }
    write_reports(payload)
    print(json.dumps({"ok": ok, "json_out": str(REPORT_JSON), "md_out": str(REPORT_MD)}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
