from __future__ import annotations

import copy

from .agent_skill_policy import (
    ensure_skill_visible,
    resolve_default_agent_id,
    skill_is_visible,
    strip_authorized_skill_addition,
)
from .profile_tool_policy import (
    approved_tools_are_profile_visible,
    enable_profile_tools,
    strip_authorized_tool_change,
)
from .selftest_telemetry import TOOLS


SAMPLE_SKILL = "sample-routing-skill"
PROFILE = "coding"
PROFILE_EXPANSION = ("group:fs", "group:runtime", "group:web")


def test_agent_skill_policy() -> None:
    unrestricted: dict = {}
    unrestricted_change = ensure_skill_visible(unrestricted, SAMPLE_SKILL)
    assert unrestricted_change.unrestricted is True
    assert unrestricted_change.changed is False
    assert resolve_default_agent_id(unrestricted) == "main"
    assert skill_is_visible(unrestricted, SAMPLE_SKILL, "main") is True

    defaults = {"agents": {"defaults": {"skills": ["existing-skill"]}}}
    defaults_before = copy.deepcopy(defaults)
    defaults_change = ensure_skill_visible(defaults, SAMPLE_SKILL)
    assert defaults_change.scope == "defaults"
    assert defaults_change.changed is True
    assert skill_is_visible(defaults, SAMPLE_SKILL, "main") is True
    assert (
        strip_authorized_skill_addition(
            defaults,
            defaults_change,
            SAMPLE_SKILL,
        )
        == defaults_before
    )

    explicit = {
        "agents": {
            "defaults": {"skills": ["baseline-skill"]},
            "list": [
                {"id": "secondary", "skills": []},
                {"id": "primary", "default": True, "skills": ["agent-skill"]},
            ],
        }
    }
    explicit_before = copy.deepcopy(explicit)
    explicit_change = ensure_skill_visible(explicit, SAMPLE_SKILL)
    assert explicit_change.agent_id == "primary"
    assert explicit_change.scope == "agent"
    assert explicit_change.changed is True
    assert skill_is_visible(explicit, SAMPLE_SKILL, "primary") is True
    assert (
        strip_authorized_skill_addition(
            explicit,
            explicit_change,
            SAMPLE_SKILL,
        )
        == explicit_before
    )

    duplicate = {"agents": {"defaults": {"skills": ["same", "same"]}}}
    try:
        ensure_skill_visible(duplicate, SAMPLE_SKILL)
    except RuntimeError:
        pass
    else:
        raise AssertionError("duplicate skill allowlist entries must be rejected")


def _assert_profile_also_allow_scope(approved: tuple[str, ...]) -> None:
    created = {
        "tools": {
            "profile": PROFILE,
            "deny": [*approved, "write"],
        }
    }
    created_before = copy.deepcopy(created)
    change = enable_profile_tools(
        created["tools"],
        approved,
        PROFILE_EXPANSION,
        PROFILE,
    )
    assert change.allow_mode == "profile-authority-preserved"
    assert change.also_allow_mode == "created-profile-also-allow"
    assert "allow" not in created["tools"]
    assert created["tools"]["alsoAllow"] == list(approved)
    assert created["tools"]["deny"] == ["write"]
    assert approved_tools_are_profile_visible(created["tools"], approved, PROFILE)
    created_before["tools"].pop("deny")
    assert strip_authorized_tool_change(created, change) == created_before


def _assert_existing_allow_scope(approved: tuple[str, ...]) -> None:
    existing = {
        "tools": {
            "profile": PROFILE,
            "allow": ["group:runtime"],
            "deny": [*approved, "write"],
        }
    }
    existing_before = copy.deepcopy(existing)
    change = enable_profile_tools(
        existing["tools"],
        approved,
        PROFILE_EXPANSION,
        PROFILE,
    )
    assert change.allow_mode == "extended-existing-allow"
    assert change.also_allow_mode == "not-used-existing-allow"
    assert existing["tools"]["allow"] == ["group:runtime", *approved]
    assert "alsoAllow" not in existing["tools"]
    assert existing["tools"]["deny"] == ["write"]
    assert approved_tools_are_profile_visible(existing["tools"], approved, PROFILE)
    existing_before["tools"].pop("deny")
    assert strip_authorized_tool_change(existing, change) == existing_before


def _assert_existing_also_allow_scope(approved: tuple[str, ...]) -> None:
    existing = {
        "tools": {
            "profile": PROFILE,
            "alsoAllow": ["existing-tool", approved[0]],
            "deny": [*approved, "write"],
        }
    }
    existing_before = copy.deepcopy(existing)
    change = enable_profile_tools(
        existing["tools"],
        approved,
        PROFILE_EXPANSION,
        PROFILE,
    )
    assert change.allow_mode == "profile-authority-preserved"
    assert change.also_allow_mode == "extended-profile-also-allow"
    assert "allow" not in existing["tools"]
    assert existing["tools"]["alsoAllow"] == ["existing-tool", *approved]
    assert existing["tools"]["deny"] == ["write"]
    assert approved_tools_are_profile_visible(existing["tools"], approved, PROFILE)
    existing_before["tools"].pop("deny")
    assert strip_authorized_tool_change(existing, change) == existing_before


def _assert_invalid_policy_shapes(approved: tuple[str, ...]) -> None:
    dual_scope = {
        "profile": PROFILE,
        "allow": ["group:runtime"],
        "alsoAllow": [approved[0]],
        "deny": list(approved),
    }
    try:
        enable_profile_tools(dual_scope, approved, PROFILE_EXPANSION, PROFILE)
    except RuntimeError:
        pass
    else:
        raise AssertionError("dual authorization scopes must be rejected")

    duplicate = {
        "profile": PROFILE,
        "deny": list(approved),
        "alsoAllow": ["duplicate", "duplicate"],
    }
    try:
        enable_profile_tools(duplicate, approved, PROFILE_EXPANSION, PROFILE)
    except RuntimeError:
        pass
    else:
        raise AssertionError("duplicate tools.alsoAllow entries must be rejected")


def test_profile_tool_policy() -> None:
    approved = tuple(sorted(TOOLS))
    _assert_profile_also_allow_scope(approved)
    _assert_existing_allow_scope(approved)
    _assert_existing_also_allow_scope(approved)

    already_complete = {
        "tools": {
            "profile": PROFILE,
            "alsoAllow": list(approved),
            "deny": list(approved),
        }
    }
    complete_change = enable_profile_tools(
        already_complete["tools"],
        approved,
        PROFILE_EXPANSION,
        PROFILE,
    )
    assert complete_change.added_to_allow == ()
    assert complete_change.added_to_also_allow == ()
    assert already_complete["tools"]["deny"] == []
    assert approved_tools_are_profile_visible(
        already_complete["tools"],
        approved,
        PROFILE,
    )
    _assert_invalid_policy_shapes(approved)
