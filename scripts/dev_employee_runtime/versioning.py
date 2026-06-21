from __future__ import annotations

import re


_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def require_policy_version(value: object) -> str:
    version = str(value or "").strip()
    if not _VERSION_RE.fullmatch(version):
        raise ValueError("invalid policy version")
    return version
