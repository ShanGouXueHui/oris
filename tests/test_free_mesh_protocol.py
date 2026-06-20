from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.dev_employee_openclaw_enable.free_mesh_protocol import (
    endpoint_from_config,
    validate_health_payload,
)


def test_valid_protocol_v2_health() -> None:
    result = validate_health_payload(
        {
            "ok": True,
            "service": "oris-free-mesh-api",
            "protocol_version": 2,
            "tool_calling": True,
        }
    )
    assert result["accepted"] is True
    assert result["tool_calling"] is True
    assert result["protocol_version"] == 2
    assert result["raw_response_recorded"] is False


def test_text_only_health_is_rejected() -> None:
    result = validate_health_payload(
        {
            "ok": True,
            "service": "oris-free-mesh-api",
        }
    )
    assert result["accepted"] is False
    assert result["tool_calling"] is False


def test_endpoint_must_be_loopback() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        config_dir = root / "config"
        config_dir.mkdir()
        (config_dir / "oris_free_mesh_api.json").write_text(
            json.dumps({"host": "0.0.0.0", "port": 8789}),
            encoding="utf-8",
        )
        raised = False
        try:
            endpoint_from_config(root)
        except RuntimeError:
            raised = True
        assert raised


def test_endpoint_uses_configured_loopback_port() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        config_dir = root / "config"
        config_dir.mkdir()
        (config_dir / "oris_free_mesh_api.json").write_text(
            json.dumps({"host": "127.0.0.1", "port": 9876}),
            encoding="utf-8",
        )
        host, port, endpoint = endpoint_from_config(root)
        assert host == "127.0.0.1"
        assert port == 9876
        assert endpoint == "http://127.0.0.1:9876/v1/health"


def run_all() -> None:
    test_valid_protocol_v2_health()
    test_text_only_health_is_rejected()
    test_endpoint_must_be_loopback()
    test_endpoint_uses_configured_loopback_port()


if __name__ == "__main__":
    run_all()
