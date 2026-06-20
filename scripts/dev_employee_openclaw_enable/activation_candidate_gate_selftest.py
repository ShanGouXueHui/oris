from __future__ import annotations

import copy

from .activation_candidate_gate import validate_activation_candidate_result


def _application() -> dict[str, object]:
    return {
        "tool_policy": {
            "allow_added_count": 0,
            "also_allow_added_count": 3,
        },
        "skill_policy": {
            "changed": False,
            "scope": "unrestricted",
        },
    }


def _compatibility() -> dict[str, object]:
    return {
        "status": "PASS",
        "authorization_scope": "profile-plus-alsoAllow",
        "checks": {
            "profile_matches": True,
            "single_authorization_scope": True,
            "authorization_scope_present": True,
            "approved_authorized": True,
            "approved_removed_from_deny": True,
            "routing_skill_visible": True,
        },
    }


def _runtime_validation() -> dict[str, object]:
    return {
        "status": "PASS",
        "validator": "config.patch.dry-run",
        "active_config_unchanged": True,
        "active_config_written": False,
        "policy_patch": {
            "changed_paths": ["tools.alsoAllow", "tools.deny"],
        },
        "validation_diagnostics": {
            "ok": True,
            "error_count": 0,
            "checks": {
                "schema": True,
                "resolvability": True,
                "resolvabilityComplete": True,
            },
            "raw_output_recorded": False,
            "secret_refs_recorded": False,
        },
    }


def run_activation_candidate_gate_selftests() -> bool:
    valid = validate_activation_candidate_result(
        _application(),
        _compatibility(),
        _runtime_validation(),
    )
    assert valid["status"] == "PASS"
    assert valid["changed_paths"] == ["tools.alsoAllow", "tools.deny"]

    dual_scope = copy.deepcopy(_application())
    dual_scope["tool_policy"]["allow_added_count"] = 3
    try:
        validate_activation_candidate_result(
            dual_scope,
            _compatibility(),
            _runtime_validation(),
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("dual authorization scope was accepted")

    unexpected_path = copy.deepcopy(_runtime_validation())
    unexpected_path["policy_patch"]["changed_paths"].append("gateway.port")
    try:
        validate_activation_candidate_result(
            _application(),
            _compatibility(),
            unexpected_path,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("unexpected candidate path was accepted")

    unsafe_output = copy.deepcopy(_runtime_validation())
    unsafe_output["validation_diagnostics"]["raw_output_recorded"] = True
    try:
        validate_activation_candidate_result(
            _application(),
            _compatibility(),
            unsafe_output,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("unsafe runtime output evidence was accepted")
    return True
