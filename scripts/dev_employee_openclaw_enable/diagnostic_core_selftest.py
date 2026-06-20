from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from . import skill as skill_facade
from .candidate_validation import candidate_policy_compatibility
from .models import CheckRecorder, stage_status
from .profile_tool_policy import enable_profile_tools
from .runtime_policy_patch import build_policy_validation_patch
from .runtime_validation_output import summarize_dry_run_output
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


def _assert_single_scope_transform() -> None:
    tools = {
        "profile": "coding",
        "deny": ["tool_a", "tool_b", "tool_c"],
    }
    change = enable_profile_tools(
        tools,
        ("tool_a", "tool_b", "tool_c"),
        ("group:fs", "group:runtime"),
        "coding",
    )
    assert "allow" not in tools
    assert tools["alsoAllow"] == ["tool_a", "tool_b", "tool_c"]
    assert tools["deny"] == []
    assert change.added_to_allow == ()
    assert change.added_to_also_allow == ("tool_a", "tool_b", "tool_c")
    assert change.allow_mode == "profile-authority-preserved"


def _assert_policy_patch_builder() -> None:
    active = {
        "tools": {
            "profile": "coding",
            "deny": ["tool_a", "tool_b", "tool_c"],
            "unrelated": {"privateValue": "must-not-be-copied"},
        },
        "agents": {"defaults": {"skills": ["existing-skill"]}},
        "gateway": {"token": "must-not-be-copied"},
    }
    candidate = {
        "tools": {
            "profile": "coding",
            "alsoAllow": ["tool_a", "tool_b", "tool_c"],
            "deny": [],
            "unrelated": {"privateValue": "redacted"},
        },
        "agents": {
            "defaults": {"skills": ["existing-skill", "sample-routing-skill"]}
        },
        "gateway": {"token": "redacted"},
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        active_path = root / "active.json"
        candidate_path = root / "candidate.json"
        active_path.write_text(json.dumps(active), encoding="utf-8")
        candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
        context = SimpleNamespace(openclaw_config=active_path)
        patch_path, replace_paths, evidence = build_policy_validation_patch(
            context,
            candidate_path,
        )
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
    assert replace_paths == ()
    assert set(patch) == {"tools", "agents"}
    assert set(patch["tools"]) == {"alsoAllow", "deny"}
    assert patch["agents"]["defaults"]["skills"][-1] == "sample-routing-skill"
    assert "gateway" not in patch
    assert "unrelated" not in patch["tools"]
    assert evidence["changed_paths"] == [
        "tools.alsoAllow",
        "tools.deny",
        "agents.defaults.skills",
    ]
    assert evidence["patch_content_recorded"] is False


def _compatibility_context() -> SimpleNamespace:
    return SimpleNamespace(
        approved_tools=("tool_a", "tool_b", "tool_c"),
        profile_expansion=("group:fs", "group:runtime"),
        required_profile="coding",
        routing_skill_name="sample-routing-skill",
    )


def _assert_candidate_compatibility() -> None:
    valid = {
        "tools": {
            "profile": "coding",
            "alsoAllow": ["tool_a", "tool_b", "tool_c"],
            "deny": ["other"],
        }
    }
    invalid = {
        "tools": {
            "profile": "coding",
            "allow": ["group:fs", "tool_a", "tool_b", "tool_c"],
            "alsoAllow": ["tool_a", "tool_b", "tool_c"],
            "deny": ["other"],
        }
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        valid_path = root / "valid.json"
        invalid_path = root / "invalid.json"
        valid_path.write_text(json.dumps(valid), encoding="utf-8")
        invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
        valid_result = candidate_policy_compatibility(
            _compatibility_context(),
            valid_path,
        )
        invalid_result = candidate_policy_compatibility(
            _compatibility_context(),
            invalid_path,
        )
    assert valid_result["status"] == "PASS"
    assert valid_result["authorization_scope"] == "profile-plus-alsoAllow"
    assert valid_result["checks"]["routing_skill_visible"] is True
    assert invalid_result["status"] == "FAIL"
    assert invalid_result["checks"]["single_authorization_scope"] is False


def _assert_sanitized_runtime_output() -> None:
    raw = json.dumps(
        {
            "ok": False,
            "operations": 3,
            "inputModes": ["json"],
            "checks": {
                "schema": True,
                "resolvability": True,
                "resolvabilityComplete": True,
            },
            "refsChecked": 0,
            "skippedExecRefs": 0,
            "errors": [
                {
                    "kind": "schema",
                    "message": "tools policy cannot set both allow and alsoAllow in the same scope",
                }
            ],
        }
    )
    summary = summarize_dry_run_output(raw)
    assert summary["json_parsed"] is True
    assert summary["error_count"] == 1
    assert summary["errors"][0]["rule_code"] == (
        "tools_allow_also_allow_mutually_exclusive"
    )
    assert "message" not in summary["errors"][0]


def run_core_diagnostic_selftests() -> bool:
    _assert_skill_facade()
    _assert_single_scope_transform()
    _assert_policy_patch_builder()
    _assert_candidate_compatibility()
    _assert_sanitized_runtime_output()
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
    return True
