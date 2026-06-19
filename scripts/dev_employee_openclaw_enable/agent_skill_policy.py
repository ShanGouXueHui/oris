from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentSkillPolicyChange:
    agent_id: str
    scope: str
    changed: bool
    unrestricted: bool
    before_count: int
    after_count: int

    @property
    def mode(self) -> str:
        if self.unrestricted:
            return "skill-unrestricted"
        if self.changed:
            return f"skill-added-to-{self.scope}"
        return f"skill-already-visible-via-{self.scope}"

    def evidence(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "scope": self.scope,
            "changed": self.changed,
            "unrestricted": self.unrestricted,
            "before_count": self.before_count,
            "after_count": self.after_count,
            "secret_values_recorded": False,
        }


def _agents(config: dict[str, Any]) -> dict[str, Any]:
    value = config.get("agents")
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RuntimeError("OpenClaw agents configuration is invalid")
    return value


def _agent_entries(agents: dict[str, Any]) -> list[dict[str, Any]]:
    value = agents.get("list")
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise RuntimeError("OpenClaw agents.list is invalid")
    return value


def resolve_default_agent_id(config: dict[str, Any]) -> str:
    entries = _agent_entries(_agents(config))
    defaults = [
        item
        for item in entries
        if item.get("default") is True and isinstance(item.get("id"), str)
    ]
    if len(defaults) > 1:
        raise RuntimeError("multiple OpenClaw agents are marked default")
    if defaults:
        return str(defaults[0]["id"])
    for item in entries:
        value = item.get("id")
        if isinstance(value, str) and value:
            return value
    return "main"


def _find_agent_entry(
    agents: dict[str, Any],
    agent_id: str,
) -> dict[str, Any] | None:
    for item in _agent_entries(agents):
        if item.get("id") == agent_id:
            return item
    return None


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RuntimeError(f"{label} must be a string list")
    if len(value) != len(set(value)):
        raise RuntimeError(f"{label} contains duplicate entries")
    return value


def ensure_skill_visible(
    config: dict[str, Any],
    skill_name: str,
) -> AgentSkillPolicyChange:
    agents = _agents(config)
    agent_id = resolve_default_agent_id(config)
    agent_entry = _find_agent_entry(agents, agent_id)

    if agent_entry is not None and "skills" in agent_entry:
        values = _string_list(agent_entry["skills"], f"agent {agent_id} skills")
        before_count = len(values)
        changed = skill_name not in values
        if changed:
            values.append(skill_name)
        return AgentSkillPolicyChange(
            agent_id=agent_id,
            scope="agent",
            changed=changed,
            unrestricted=False,
            before_count=before_count,
            after_count=len(values),
        )

    defaults = agents.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        raise RuntimeError("OpenClaw agents.defaults is invalid")
    if isinstance(defaults, dict) and "skills" in defaults:
        values = _string_list(defaults["skills"], "agents.defaults.skills")
        before_count = len(values)
        changed = skill_name not in values
        if changed:
            values.append(skill_name)
        return AgentSkillPolicyChange(
            agent_id=agent_id,
            scope="defaults",
            changed=changed,
            unrestricted=False,
            before_count=before_count,
            after_count=len(values),
        )

    return AgentSkillPolicyChange(
        agent_id=agent_id,
        scope="unrestricted",
        changed=False,
        unrestricted=True,
        before_count=0,
        after_count=0,
    )


def skill_is_visible(
    config: dict[str, Any],
    skill_name: str,
    expected_agent_id: str,
) -> bool:
    if resolve_default_agent_id(config) != expected_agent_id:
        return False
    agents = _agents(config)
    entry = _find_agent_entry(agents, expected_agent_id)
    if entry is not None and "skills" in entry:
        return skill_name in _string_list(
            entry["skills"],
            f"agent {expected_agent_id} skills",
        )
    defaults = agents.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        return False
    if isinstance(defaults, dict) and "skills" in defaults:
        return skill_name in _string_list(defaults["skills"], "agents.defaults.skills")
    return True


def strip_authorized_skill_addition(
    config: dict[str, Any],
    change: AgentSkillPolicyChange,
    skill_name: str,
) -> dict[str, Any]:
    copied = copy.deepcopy(config)
    if not change.changed:
        return copied
    agents = _agents(copied)
    target: list[str] | None = None
    if change.scope == "agent":
        entry = _find_agent_entry(agents, change.agent_id)
        if entry is not None:
            target = _string_list(entry.get("skills"), "authorized agent skills")
    elif change.scope == "defaults":
        defaults = agents.get("defaults")
        if isinstance(defaults, dict):
            target = _string_list(
                defaults.get("skills"),
                "authorized default skills",
            )
    if target is None or target.count(skill_name) != 1:
        raise RuntimeError("authorized routing skill addition is missing or duplicated")
    target.remove(skill_name)
    return copied
