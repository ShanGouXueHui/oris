from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from . import skill as skill_facade
from .candidate_validation import candidate_policy_compatibility
from .models import CheckRecorder, stage_status
from .skill_installation import (
    SkillBackup,
    SkillPathBackup,
    backup_routing_skill,
    install_routing_skill,
    restore_routing_skill,
    validate_skill_install_target,
)
from .skill_runtime import verify_routing_skill_runtime


def _assert_skill_facade() -> None:
    assert skill_facade.SkillBackup is SkillBackup
    assert skill_facade.SkillPathBackup is SkillPathBackup
    assert skill_facade.backup_routing_skill is backup_routing_skill
    assert skill_facade.install_routing_skill is install_routing_skill
    assert skill_facade.restore_routing_skill is restore_routing_skill
    assert skill_facade.validate_skill_install_target is validate_skill_install_target
    assert skill_facade.verify_routing_skill_runtime is verify_routing_skill_runtime


def run_core_diagnostic_selftests() -> bool:
    _assert_skill_facade()
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
