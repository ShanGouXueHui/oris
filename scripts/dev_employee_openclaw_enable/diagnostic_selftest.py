from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from .candidate_validation import candidate_policy_compatibility
from .models import CheckRecorder, stage_status
from .service_control import _safe_rows


def _test_check_recorder_tri_state() -> None:
    recorder = CheckRecorder()
    recorder.pass_check("pass", "ok")
    recorder.fail_check("fail", "bad")
    recorder.not_checked("later", "blocked")
    assert recorder.pass_count == 1
    assert recorder.fail_count == 1
    assert recorder.not_checked_count == 1
    assert [item["status"] for item in recorder.checks] == [
        "PASS",
        "FAIL",
        "NOT_CHECKED",
    ]


def _test_stage_status() -> None:
    assert stage_status(True) == "PASS"
    assert stage_status(False) == "FAIL"
    assert stage_status(None) == "NOT_CHECKED"


def _test_service_redaction() -> None:
    rows = _safe_rows(
        "normal line\nauthorization=private-value\n"
        'drop {"token":"private-value"}\n',
        10,
    )
    assert rows == ["normal line"]
    assert "private-value" not in "\n".join(rows)


def _test_candidate_compatibility() -> None:
    context = SimpleNamespace(
        approved_tools=("tool_a", "tool_b", "tool_c"),
        profile_expansion=("group:fs", "group:runtime"),
        required_profile="coding",
    )
    candidate = {
        "tools": {
            "profile": "coding",
            "allow": ["group:fs", "group:runtime", "tool_a", "tool_b", "tool_c"],
            "alsoAllow": ["tool_a", "tool_b", "tool_c"],
            "deny": ["other"],
        }
    }
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "candidate.json"
        path.write_text(json.dumps(candidate), encoding="utf-8")
        result = candidate_policy_compatibility(context, path)
    assert result["status"] == "PASS"
    assert result["candidate_config_recorded"] is False


def run_diagnostic_selftests() -> bool:
    _test_check_recorder_tri_state()
    _test_stage_status()
    _test_service_redaction()
    _test_candidate_compatibility()
    return True
