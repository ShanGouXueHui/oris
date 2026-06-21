from __future__ import annotations

from urllib.parse import urlparse


def require_loopback_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("loopback HTTP URL required")
    if parsed.port is None:
        raise ValueError("explicit loopback port required")
    return value
