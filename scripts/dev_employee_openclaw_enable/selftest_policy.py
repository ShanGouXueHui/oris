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


def test_profile_tool_policy() -> None:
    approved = tuple(sorted(TOOLS))
    created = {
        "tools": {
            "profile": PROFILE,
            "deny": [*approved, "write"],
        }
    }
    created_before = copy.deepcopy(created)
    created_change = enable_profile_tools(
        created["tools"],
        approved,
        PROFILE_EXPANSION,
        PROFILE,
    )
    assert created_change.allow_mode == "materialized-profile-plus-approved"
    assert created_change.also_allow_mode == "created-profile-also-allow"
    assert created["tools"]["allow"] == [*PROFILE_EXPANSION, *approved]
    assert created["tools"]["alsoAllow"] == list(approved)
    assert approved_tools_are_profile_visible(created["tools"], approved, PROFILE)
    created_before["tools"].pop("deny")
    assert strip_authorized_tool_change(created, created_change) == created_before

    existing = {
        "tools": {
            "profile": PROFILE,
            "allow": ["group:runtime"],
            "alsoAllow": ["existing-tool", approved[0]],
            "deny": [*approved, "write"],
        }
    }
    existing_before = copy.deepcopy(existing)
    existing_change = enable_profile_tools(
        existing["tools"],
        approved,
        PROFILE_EXPANSION,
        PROFILE,
    )
    assert existing_change.allow_mode == "preserved-allow-plus-approved"
    assert existing_change.also_allow_mode == "extended-profile-also-allow"
    assert existing["tools"]["allow"] == ["group:runtime", *approved]
    assert existing["tools"]["alsoAllow"] == ["existing-tool", *approved]
    assert approved_tools_are_profile_visible(existing["tools"], approved, PROFILE)
    existing_before["tools"].pop("deny")
    assert strip_authorized_tool_change(existing, existing_change) == existing_before

    already_complete = {
        "tools": {
            "profile": PROFILE,
            "allow": [*PROFILE_EXPANSION, *approved],
            "alsoAllow": list(approved),
            "deny": [*approved],
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
    assert approved_tools_are_profile_visible(
        already_complete["tools"],
        approved,
        PROFILE,
    )

    invalid = {
        "profile": PROFILE,
        "deny": list(approved),
        "alsoAllow": ["duplicate", "duplicate"],
    }
    try:
        enable_profile_tools(invalid, approved, PROFILE_EXPANSION, PROFILE)
    except RuntimeError:
        pass
    else:
        raise AssertionError("duplicate tools.alsoAllow entries must be rejected")
