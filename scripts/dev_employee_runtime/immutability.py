from __future__ import annotations

from typing import Any

from .audit import stable_hash


def verify_immutable_record(record: dict[str, Any], expected_hash: str) -> None:
    material = {key: value for key, value in record.items() if key != "record_hash"}
    if stable_hash(material) != expected_hash:
        raise RuntimeError("immutable record hash mismatch")
