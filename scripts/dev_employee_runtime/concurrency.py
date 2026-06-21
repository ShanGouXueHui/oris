from __future__ import annotations


def require_expected_version(*, actual: int, expected: int) -> None:
    if actual != expected:
        raise RuntimeError(
            f"optimistic concurrency conflict: expected version {expected}, actual {actual}"
        )
