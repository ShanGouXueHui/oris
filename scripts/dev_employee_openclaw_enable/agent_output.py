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
