from __future__ import annotations

import subprocess
from pathlib import Path

from .code_audit_cli import audit_code_state
from .context import discover_repo_root
from .free_mesh_protocol import FREE_MESH_SERVICE, probe_free_mesh_protocol


def _summary(result: str, failure_code: str, next_action: str) -> None:
    print("===== SUMMARY =====")
    print(f"RESULT={result}")
    print(f"FAILURE_CODE={failure_code}")
    print("FREE_MESH_RESTARTED=NO")
    print("OPENCLAW_ACCESSED=NO")
    print("GATEWAY_RESTARTED=NO")
    print("TASK_SUBMITTED=NO")
    print(f"NEXT_ACTION={next_action}")
    print("SEND_TO_CHAT=THIS_SUMMARY_ONLY")
    print("===== END SUMMARY =====")


def main() -> int:
    repo_root = discover_repo_root()
    audit, _, contract_error = audit_code_state(repo_root)
    if not audit.get("ok"):
        _summary(
            "FREE_MESH_PROTOCOL_ACTIVATION_BLOCKED",
            contract_error or "code_audit_findings",
            "FIX_ALL_CODE_AUDIT_FINDINGS",
        )
        return 2

    restart = subprocess.run(
        ["systemctl", "--user", "restart", FREE_MESH_SERVICE],
        capture_output=True,
        text=True,
        check=False,
    )
    protocol = probe_free_mesh_protocol(repo_root)
    if restart.returncode != 0 or protocol.get("status") != "PASS":
        print("===== SUMMARY =====")
        print("RESULT=FREE_MESH_PROTOCOL_ACTIVATION_FAILED")
        print(
            "FAILURE_CODE="
            + (
                "free_mesh_service_restart_failed"
                if restart.returncode != 0
                else "free_mesh_protocol_v2_not_ready"
            )
        )
        print(f"FREE_MESH_SERVICE_STATE={protocol.get('service_state')}")
        print(f"FREE_MESH_PROTOCOL_VERSION={protocol.get('protocol_version')}")
        print(
            "FREE_MESH_TOOL_CALLING="
            + ("YES" if protocol.get("tool_calling") else "NO")
        )
        print("FREE_MESH_RESTARTED=YES")
        print("OPENCLAW_ACCESSED=NO")
        print("GATEWAY_RESTARTED=NO")
        print("TASK_SUBMITTED=NO")
        print("NEXT_ACTION=READ_FREE_MESH_SERVICE_JOURNAL")
        print("SEND_TO_CHAT=THIS_SUMMARY_ONLY")
        print("===== END SUMMARY =====")
        return 1

    diagnostic = repo_root / "scripts" / "dev_employee_diagnose_openclaw_model_tool_call_routing.sh"
    result = subprocess.run(
        ["bash", str(diagnostic)],
        cwd=Path(repo_root),
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
