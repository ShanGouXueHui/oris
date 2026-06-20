from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


_SHA = re.compile(r"[0-9a-f]{40}")


def load_json_object(path: Path) -> dict[str, Any]:
    duplicates: list[str] = []

    def collect(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=collect)
    if duplicates:
        raise RuntimeError("duplicate JSON keys: " + ",".join(sorted(set(duplicates))))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path.name}")
    return value


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"invalid mapping: {label}")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"invalid string: {label}")
    return value


def require_boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise RuntimeError(f"invalid boolean: {label}")
    return value


def require_integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError(f"invalid integer: {label}")
    return value


def require_unique_strings(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise RuntimeError(f"invalid string list: {label}")
    if len(value) != len(set(value)):
        raise RuntimeError(f"duplicate string list entry: {label}")
    return tuple(value)


def require_unique_integers(value: Any, label: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not all(isinstance(item, int) and not isinstance(item, bool) for item in value):
        raise RuntimeError(f"invalid integer list: {label}")
    if len(value) != len(set(value)):
        raise RuntimeError(f"duplicate integer list entry: {label}")
    return tuple(value)


def load_task_id(path: Path) -> str:
    return require_string(load_json_object(path).get("task_id"), "current_task.task_id")


def load_runtime_contract(path: Path) -> dict[str, Any]:
    root = load_json_object(path)
    if root.get("schema_version") != 3:
        raise RuntimeError("unsupported acceptance contract schema")
    runtime = require_mapping(root.get("runtime"), "runtime")
    plugin = require_mapping(root.get("plugin"), "plugin")
    baseline = require_mapping(root.get("baseline"), "baseline")
    routes = require_mapping(root.get("public_routes"), "public_routes")
    skill = require_mapping(root.get("routing_skill"), "routing_skill")
    tools = require_mapping(root.get("tool_policy"), "tool_policy")
    agent = require_mapping(root.get("agent_acceptance"), "agent_acceptance")
    telemetry = require_mapping(root.get("telemetry"), "telemetry")
    evidence = require_mapping(root.get("evidence"), "evidence")

    version = require_string(runtime.get("openclaw_version"), "runtime.openclaw_version")
    gateway_url = require_string(runtime.get("gateway_url"), "runtime.gateway_url").rstrip("/")
    gateway = urlparse(gateway_url)
    if gateway.scheme != "http" or gateway.hostname not in {"127.0.0.1", "localhost", "::1"} or gateway.port is None:
        raise RuntimeError("runtime.gateway_url must be loopback HTTP with a port")
    public_url = require_string(runtime.get("public_url"), "runtime.public_url").rstrip("/")
    public = urlparse(public_url)
    if public.scheme != "https" or not public.hostname:
        raise RuntimeError("runtime.public_url must be HTTPS")
    internal_ports = require_unique_integers(runtime.get("internal_ports"), "runtime.internal_ports")
    if gateway.port in internal_ports:
        raise RuntimeError("Gateway port must differ from internal ORIS ports")

    profile = require_string(tools.get("required_profile"), "tool_policy.required_profile")
    expansions = require_mapping(tools.get("profile_expansions"), "tool_policy.profile_expansions")
    version_expansion = require_mapping(expansions.get(version), "tool_policy.profile_expansions.runtime")
    approved_tools = require_unique_strings(tools.get("approved_tools"), "tool_policy.approved_tools")
    profile_expansion = require_unique_strings(version_expansion.get(profile), "tool_policy.profile_expansion")
    hooks = require_unique_strings(telemetry.get("required_events"), "telemetry.required_events")

    raw_turns = agent.get("turns")
    if not isinstance(raw_turns, list) or not all(isinstance(item, dict) for item in raw_turns):
        raise RuntimeError("invalid agent_acceptance.turns")
    turns = tuple(dict(item) for item in raw_turns)
    expected_tools = tuple(require_string(item.get("expected_tool"), "agent_acceptance.turn.expected_tool") for item in turns)
    if len(expected_tools) != len(set(expected_tools)) or set(expected_tools) != set(approved_tools):
        raise RuntimeError("agent acceptance tools differ from approved tools")

    commit = require_string(baseline.get("expected_commit"), "baseline.expected_commit")
    if _SHA.fullmatch(commit) is None:
        raise RuntimeError("baseline.expected_commit must be a full commit SHA")
    if require_string(skill.get("install_scope"), "routing_skill.install_scope") != "global":
        raise RuntimeError("routing skill install scope must be global")

    return {
        "runtime": runtime,
        "plugin": plugin,
        "baseline": baseline,
        "routes": routes,
        "skill": skill,
        "tools": tools,
        "agent": agent,
        "evidence": evidence,
        "runtime_version": version,
        "gateway_url": gateway_url,
        "public_url": public_url,
        "internal_ports": internal_ports,
        "required_profile": profile,
        "profile_expansion": profile_expansion,
        "approved_tools": approved_tools,
        "required_hooks": hooks,
        "turns": turns,
        "expected_commit": commit,
    }
