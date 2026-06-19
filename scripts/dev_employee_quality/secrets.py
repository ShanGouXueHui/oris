from __future__ import annotations

import json
from typing import Any

from .models import Finding, SourceFile


SECRET_KEY_NAMES = {
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "credential",
    "credentials",
    "private_key",
}
REFERENCE_SUFFIXES = ("_ref", "_reference", "_secret_ref")
REFERENCE_PREFIXES = ("secrets_json:", "env:", "file:", "vault:", "secret:")


def _is_secret_key(key: str) -> bool:
    normalized = key.strip().lower()
    if normalized.endswith(REFERENCE_SUFFIXES):
        return False
    return normalized in SECRET_KEY_NAMES or normalized.endswith("_password") or normalized.endswith("_token")


def _is_reference(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized.startswith(REFERENCE_PREFIXES) or normalized.startswith("${")


def _walk(value: Any, path: tuple[str, ...], findings: list[Finding], source: SourceFile) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, str(key))
            if _is_secret_key(str(key)) and isinstance(child, str) and child.strip() and not _is_reference(child):
                findings.append(
                    Finding(
                        "plaintext_secret",
                        source.relative_path,
                        1,
                        "plaintext secret-like value must be replaced by a secret reference and rotated",
                        ".".join(child_path),
                    )
                )
            _walk(child, child_path, findings, source)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk(child, (*path, str(index)), findings, source)


def scan_json_secrets(source: SourceFile) -> list[Finding]:
    try:
        payload = json.loads(source.text)
    except json.JSONDecodeError:
        return []
    findings: list[Finding] = []
    _walk(payload, (), findings, source)
    return findings
