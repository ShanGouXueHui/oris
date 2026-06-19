from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from .candidate_validation import candidate_policy_compatibility
from .models import CheckRecorder, stage_status


def run_core_diagnostic_selftests() -> bool:
    recorder = CheckRecorder()
    recorder.pass_check("pass", "ok")
    recorder.fail_check("fail", "bad")
    recorder.not_checked("later", "blocked")
    assert recorder.pass_count == 1
    assert recorder.fail_count == 1
    assert recorder.not_checked_count == 1
    assert stage_status(True) == "PASS"
    assert stage_status(False) == "FAIL"
    assert stage_status(None) == "NOT_CHECKED"

    context = SimpleNamespace(
        approved_tools=("tool_a", "tool_b", "tool_c"),
        profile_expansion=("group:fs", "group:runtime"),
        required_profile="coding",
        routing_skill_name="sample-routing-skill",
    )
    candidate = {
        "tools": {
            "profile": "coding",
            "allow": ["group:fs", "group:runtime", "tool_a", "tool_b", "tool_c"],
            "alsoAllow": ["tool_a", "tool_b", "tool_c"],
            "deny": ["other"],
        }
    }
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "candidate.json"
        path.write_text(json.dumps(candidate), encoding="utf-8")
        result = candidate_policy_compatibility(context, path)
    assert result["status"] == "PASS"
    assert result["checks"]["routing_skill_visible"] is True
    return True
