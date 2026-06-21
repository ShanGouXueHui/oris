from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dev_employee_runtime.activation import ActivationState
from dev_employee_runtime.config_loader import load_config_object
from dev_employee_runtime.paths import discover_repo_root
from dev_employee_runtime.storage_layout import StorageLayout


@dataclass(frozen=True)
class TypedActionPolicy:
    action: str
    permission: str
    risk_tier: str
    approval_required: bool
    approval_ttl_seconds: int
    allowed_payload_keys: tuple[str, ...]


@dataclass(frozen=True)
class TypedProjectPolicy:
    project_key: str
    allowed_actions: tuple[str, ...]
    allowed_scopes: tuple[str, ...]
    forbidden_scopes: tuple[str, ...]


@dataclass(frozen=True)
class TypedWritePolicy:
    policy_version: str
    activation: ActivationState
    role_permissions: dict[str, tuple[str, ...]]
    actions: dict[str, TypedActionPolicy]
    projects: dict[str, TypedProjectPolicy]
    require_approval_separation: bool
    storage: StorageLayout

    def action(self, name: str) -> TypedActionPolicy:
        try:
            return self.actions[name]
        except KeyError as exc:
            raise ValueError(f"unknown typed write action: {name}") from exc

    def project(self, key: str) -> TypedProjectPolicy:
        return self.projects.get(key) or self.projects["default"]


def load_typed_write_policy(repo_root: Path | None = None) -> TypedWritePolicy:
    root = repo_root or discover_repo_root()
    raw = load_config_object(root / "config" / "dev_employee" / "typed_write_actions_policy.json", schema_version=1)
    activation = ActivationState(**raw["activation"])
    actions = {
        name: TypedActionPolicy(
            action=name,
            permission=str(value["permission"]),
            risk_tier=str(value["risk_tier"]),
            approval_required=bool(value["approval_required"]),
            approval_ttl_seconds=int(value["approval_ttl_seconds"]),
            allowed_payload_keys=tuple(str(item) for item in value.get("allowed_payload_keys", [])),
        )
        for name, value in raw["actions"].items()
    }
    projects = {
        name: TypedProjectPolicy(
            project_key=name,
            allowed_actions=tuple(str(item) for item in value.get("allowed_actions", [])),
            allowed_scopes=tuple(str(item) for item in value.get("allowed_scopes", [])),
            forbidden_scopes=tuple(str(item) for item in value.get("forbidden_scopes", [])),
        )
        for name, value in raw["projects"].items()
    }
    role_permissions = {
        role: tuple(str(item) for item in permissions)
        for role, permissions in raw["role_permissions"].items()
    }
    storage = StorageLayout(root / str(raw["storage_root"]))
    return TypedWritePolicy(
        policy_version=str(raw["policy_version"]),
        activation=activation,
        role_permissions=role_permissions,
        actions=actions,
        projects=projects,
        require_approval_separation=bool(raw.get("approval", {}).get("require_separation", True)),
        storage=storage,
    )
