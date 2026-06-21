from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from dev_employee_runtime.typed_write_policy import load_typed_write_policy
from dev_employee_runtime.typed_write_service import TypedWriteService, runtime_dispatch


def write_policy(root: Path) -> None:
    policy_path = root / "config" / "dev_employee" / "typed_write_actions_policy.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "policy_version": "test-policy-v1",
                "activation": {"registered": False, "enabled": False},
                "storage_root": "run/typed-write-test",
                "role_permissions": {
                    "operator": ["typed_write.prepare", "typed_write.cancel", "typed_write.retry"],
                    "approver": ["typed_write.approve"],
                },
                "actions": {
                    "task_descriptor.prepare": {
                        "permission": "typed_write.prepare",
                        "risk_tier": "medium",
                        "approval_required": True,
                        "approval_ttl_seconds": 3600,
                        "allowed_payload_keys": ["objective", "paths", "metadata"],
                    }
                },
                "projects": {
                    "default": {
                        "allowed_actions": ["task_descriptor.prepare"],
                        "allowed_scopes": ["src", "tests"],
                        "forbidden_scopes": [".git", "secrets"],
                    }
                },
                "approval": {"require_separation": True},
            },
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def assert_raises(exc_type: type[BaseException], expected: str, func) -> None:
    try:
        func()
    except exc_type as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError(f"expected {exc_type.__name__}")


def test_prepare_idempotency_approval_and_finalize() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "orchestration").mkdir()
        (root / "scripts").mkdir()
        write_policy(root)
        policy = load_typed_write_policy(root)
        service = TypedWriteService(policy)
        payload = {"objective": "prepare a typed operation", "paths": ["src/app.py"], "metadata": {"token": "redact-me"}}

        first = service.prepare(
            actor_id="alice",
            actor_roles=("operator",),
            project_key="default",
            action="task_descriptor.prepare",
            payload=payload,
        )
        second = service.prepare(
            actor_id="alice",
            actor_roles=("operator",),
            project_key="default",
            action="task_descriptor.prepare",
            payload=payload,
        )
        assert second["operation_id"] == first["operation_id"]
        assert_raises(
            ValueError,
            "separation",
            lambda: service.approve(operation_id=first["operation_id"], approver_id="alice", approver_roles=("approver",)),
        )

        approval = service.approve(operation_id=first["operation_id"], approver_id="bob", approver_roles=("approver",))
        assert approval["decision"] == "approved"
        final = service.finalize_prepared(operation_id=first["operation_id"], actor_id="alice")
        assert final["runtime_dispatch"] is False
        assert final["product_mutation"] is False

        audit_text = (policy.storage.audit / "typed_write.jsonl").read_text(encoding="utf-8")
        assert "redact-me" not in audit_text
        assert "typed_write_finalized_offline" in audit_text


def test_rbac_path_scope_cancel_retry_and_runtime_dispatch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "orchestration").mkdir()
        (root / "scripts").mkdir()
        write_policy(root)
        service = TypedWriteService(load_typed_write_policy(root))

        assert_raises(
            PermissionError,
            "permission_denied",
            lambda: service.prepare(
                actor_id="eve",
                actor_roles=("approver",),
                project_key="default",
                action="task_descriptor.prepare",
                payload={"objective": "x", "paths": ["src/app.py"]},
            ),
        )
        assert_raises(
            PermissionError,
            "forbidden scope",
            lambda: service.prepare(
                actor_id="alice",
                actor_roles=("operator",),
                project_key="default",
                action="task_descriptor.prepare",
                payload={"objective": "x", "paths": ["secrets/key.txt"]},
            ),
        )

        cancel = service.cancel_operation(operation_id="op-123", actor_id="alice", reason="operator-requested")
        assert cancel["task_id"] == "op-123"

        retry = service.retry_terminal_task(
            original_task_id="task-1",
            retry_task_id="task-1-r1",
            actor_id="alice",
            reason="fixed inputs",
            original_terminal_status="failed",
        )
        assert retry["retry_task_id"] == "task-1-r1"

        assert_raises(RuntimeError, "not registered or enabled", lambda: runtime_dispatch())


if __name__ == "__main__":
    test_prepare_idempotency_approval_and_finalize()
    test_rbac_path_scope_cancel_retry_and_runtime_dispatch()
    print("typed write offline tests passed")
