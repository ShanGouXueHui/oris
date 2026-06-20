from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from .task_contract import require_unique_strings


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
        return f"skill-added-to-{self.scope}" if self.changed else f"skill-already-visible-via-{self.scope}"

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


def _entries(agents: dict[str, Any]) -> list[dict[str, Any]]:
    value = agents.get("list")
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise RuntimeError("OpenClaw agents.list is invalid")
    return value


def _skills(value: Any, label: str) -> list[str]:
    return list(require_unique_strings(value, label))


def resolve_default_agent_id(config: dict[str, Any]) -> str:
    entries = _entries(_agents(config))
    defaults = [item for item in entries if item.get("default") is True and isinstance(item.get("id"), str)]
    if len(defaults) > 1:
        raise RuntimeError("multiple OpenClaw agents are marked default")
    if defaults:
        return str(defaults[0]["id"])
    for item in entries:
        if isinstance(item.get("id"), str) and item["id"]:
            return str(item["id"])
    return "main"


def _find(agents: dict[str, Any], agent_id: str) -> dict[str, Any] | None:
    return next((item for item in _entries(agents) if item.get("id") == agent_id), None)


def ensure_skill_visible(config: dict[str, Any], skill_name: str) -> AgentSkillPolicyChange:
    agents = _agents(config)
    agent_id = resolve_default_agent_id(config)
    entry = _find(agents, agent_id)
    if entry is not None and "skills" in entry:
        values = _skills(entry["skills"], f"agent {agent_id} skills")
        before = len(values)
        changed = skill_name not in values
        if changed:
            values.append(skill_name)
        entry["skills"] = values
        return AgentSkillPolicyChange(agent_id, "agent", changed, False, before, len(values))
    defaults = agents.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        raise RuntimeError("OpenClaw agents.defaults is invalid")
    if isinstance(defaults, dict) and "skills" in defaults:
        values = _skills(defaults["skills"], "agents.defaults.skills")
        before = len(values)
        changed = skill_name not in values
        if changed:
            values.append(skill_name)
        defaults["skills"] = values
        return AgentSkillPolicyChange(agent_id, "defaults", changed, False, before, len(values))
    return AgentSkillPolicyChange(agent_id, "unrestricted", False, True, 0, 0)


def skill_is_visible(config: dict[str, Any], skill_name: str, agent_id: str) -> bool:
    if resolve_default_agent_id(config) != agent_id:
        return False
    agents = _agents(config)
    entry = _find(agents, agent_id)
    if entry is not None and "skills" in entry:
        return skill_name in _skills(entry["skills"], f"agent {agent_id} skills")
    defaults = agents.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        return False
    if isinstance(defaults, dict) and "skills" in defaults:
        return skill_name in _skills(defaults["skills"], "agents.defaults.skills")
    return True


def strip_authorized_skill_addition(
    config: dict[str, Any], change: AgentSkillPolicyChange, skill_name: str
) -> dict[str, Any]:
    copied = copy.deepcopy(config)
    if not change.changed:
        return copied
    agents = _agents(copied)
    if change.scope == "agent":
        container = _find(agents, change.agent_id)
    else:
        defaults = agents.get("defaults")
        container = defaults if isinstance(defaults, dict) else None
    if not isinstance(container, dict):
        raise RuntimeError("authorized routing skill target disappeared")
    values = _skills(container.get("skills"), "authorized routing skills")
    if values.count(skill_name) != 1:
        raise RuntimeError("authorized routing skill addition is missing or duplicated")
    values.remove(skill_name)
    container["skills"] = values
    return copied
