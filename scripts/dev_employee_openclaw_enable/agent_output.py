from __future__ import annotations

import hashlib
import json
from typing import Any


def parse_json_value(value: str) -> Any | None:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        starts = sorted(
            index
            for marker in ("{", "[")
            for index in [stripped.find(marker)]
            if index >= 0
        )
        for start in starts:
            try:
                parsed, _ = decoder.raw_decode(stripped[start:])
                return parsed
            except json.JSONDecodeError:
                continue
    return None


def parse_json_output(value: str) -> dict[str, Any] | None:
    parsed = parse_json_value(value)
    return parsed if isinstance(parsed, dict) else None


def find_transport_metadata(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, dict):
        meta = value.get("meta")
        if isinstance(meta, dict):
            transport = meta.get("transport")
            fallback_from = meta.get("fallbackFrom")
            if isinstance(transport, str) or isinstance(fallback_from, str):
                return (
                    transport if isinstance(transport, str) else None,
                    fallback_from if isinstance(fallback_from, str) else None,
                )
        for child in value.values():
            transport, fallback_from = find_transport_metadata(child)
            if transport is not None or fallback_from is not None:
                return transport, fallback_from
    elif isinstance(value, list):
        for child in value:
            transport, fallback_from = find_transport_metadata(child)
            if transport is not None or fallback_from is not None:
                return transport, fallback_from
    return None, None


def _hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def session_identifier_hashes(value: Any) -> set[str]:
    hashes: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).replace("_", "").lower()
            if (
                normalized in {"sessionid", "sessionkey"}
                and isinstance(child, str)
                and child
            ):
                hashes.add(_hash_identifier(child))
            else:
                hashes.update(session_identifier_hashes(child))
    elif isinstance(value, list):
        for child in value:
            hashes.update(session_identifier_hashes(child))
    return hashes


def reported_tool_names(value: Any, approved_tools: set[str]) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        type_value = str(
            value.get("type") or value.get("event") or value.get("kind") or ""
        ).lower()
        for key in ("toolName", "tool_name", "tool"):
            child = value.get(key)
            if isinstance(child, str) and child in approved_tools:
                names.add(child)
        if "tool" in type_value:
            child = value.get("name")
            if isinstance(child, str) and child in approved_tools:
                names.add(child)
        for child in value.values():
            names.update(reported_tool_names(child, approved_tools))
    elif isinstance(value, list):
        for child in value:
            names.update(reported_tool_names(child, approved_tools))
    return names


def _prompt_reports(value: Any) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    if isinstance(value, dict):
        tools = value.get("tools")
        skills = value.get("skills")
        tool_entries = tools.get("entries") if isinstance(tools, dict) else None
        skill_entries = skills.get("entries") if isinstance(skills, dict) else None
        if isinstance(tool_entries, list) and isinstance(skill_entries, list):
            reports.append(value)
        for child in value.values():
            reports.extend(_prompt_reports(child))
    elif isinstance(value, list):
        for child in value:
            reports.extend(_prompt_reports(child))
    return reports


def effective_tool_surface(
    value: Any,
    approved_tools: set[str],
    routing_skill_name: str,
) -> dict[str, Any]:
    reports = _prompt_reports(value)
    tool_names: set[str] = set()
    skill_names: set[str] = set()
    for report in reports:
        tools = report.get("tools")
        skills = report.get("skills")
        tool_entries = tools.get("entries") if isinstance(tools, dict) else []
        skill_entries = skills.get("entries") if isinstance(skills, dict) else []
        for entry in tool_entries if isinstance(tool_entries, list) else []:
            name = entry.get("name") if isinstance(entry, dict) else None
            if isinstance(name, str) and name:
                tool_names.add(name)
        for entry in skill_entries if isinstance(skill_entries, list) else []:
            name = entry.get("name") if isinstance(entry, dict) else None
            if isinstance(name, str) and name:
                skill_names.add(name)
    present = approved_tools.intersection(tool_names)
    missing = approved_tools - tool_names
    status = "NOT_CHECKED" if not reports else "PASS" if not missing else "FAIL"
    return {
        "status": status,
        "report_count": len(reports),
        "total_tool_count": len(tool_names),
        "approved_tools_present": sorted(present),
        "missing_approved_tools": sorted(missing),
        "routing_skill_present": routing_skill_name in skill_names,
        "other_tool_names_recorded": False,
        "system_prompt_recorded": False,
        "conversation_content_recorded": False,
    }
