from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


CheckStatus = Literal["PASS", "FAIL", "NOT_CHECKED"]


def stage_status(value: bool | None) -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "NOT_CHECKED"


@dataclass(frozen=True)
class EvidenceTarget:
    directory: Path
    filename_prefix: str
    commit_message_prefix: str


@dataclass(frozen=True)
class RuntimeContext:
    repo_root: Path
    task_id: str
    product_repo: Path
    expected_product_commit: str
    openclaw_config: Path
    backup_root: Path
    managed_skills_root: Path
    routing_skill_name: str
    routing_skill_source: Path
    routing_skill_force_replace: bool
    gateway_service: str
    gateway_url: str
    public_url: str
    public_root_route: str
    restricted_routes: tuple[str, ...]
    plugin_id: str
    plugin_version: str
    approved_tools: tuple[str, ...]
    required_hooks: tuple[str, ...]
    marker_file: Path
    internal_ports: tuple[int, ...]
    required_profile: str
    profile_expansion: tuple[str, ...]
    safe_probe_candidates: tuple[str, ...]
    direct_probe_session_key: str
    session_prefix: str
    require_gateway_transport: bool
    require_persisted_native_session: bool
    acceptance_turns: tuple[dict[str, str], ...]
    turn_timeout_seconds: int
    telemetry_wait_seconds: int
    telemetry_path: Path
    enablement_evidence: EvidenceTarget
    effective_surface_evidence: EvidenceTarget
    readiness_evidence: Path
    policy_diagnostic_evidence: EvidenceTarget | None = None

    @property
    def evidence_directory(self) -> Path:
        return self.enablement_evidence.directory

    @property
    def evidence_commit_prefix(self) -> str:
        return self.enablement_evidence.commit_message_prefix


@dataclass(frozen=True)
class RepoSnapshot:
    head: str
    remote_main: str
    status_sha256: str
    tree: str


@dataclass
class CheckRecorder:
    checks: list[dict[str, str]] = field(default_factory=list)

    def _record(self, name: str, status: CheckStatus, detail: str) -> None:
        self.checks.append({"name": name, "status": status, "detail": detail})

    def pass_check(self, name: str, detail: str) -> None:
        self._record(name, "PASS", detail)

    def fail_check(self, name: str, detail: str) -> None:
        self._record(name, "FAIL", detail)

    def not_checked(self, name: str, detail: str) -> None:
        self._record(name, "NOT_CHECKED", detail)

    @property
    def pass_count(self) -> int:
        return sum(item["status"] == "PASS" for item in self.checks)

    @property
    def fail_count(self) -> int:
        return sum(item["status"] == "FAIL" for item in self.checks)

    @property
    def not_checked_count(self) -> int:
        return sum(item["status"] == "NOT_CHECKED" for item in self.checks)


@dataclass
class RunState:
    result: str = "FAILED"
    failure_code: str = ""
    next_action: str = "INSPECT_AUTOMATIC_READONLY_ENABLEMENT_FAILURE"
    selected_policy_mode: str = "NONE"
    mutation_started: bool = False
    rollback_count: int = 0
    rollback_healthy: str = "NOT_REQUIRED"
    routing_skill_installed: bool = False
    direct_tool_calls_pass: bool | None = None
    native_agent_acceptance_pass: bool | None = None
    telemetry_privacy_pass: bool | None = None
    queue_unchanged: bool | None = None
    product_unchanged: bool | None = None
    config_scope_valid: bool | None = None
    write_tools_absent: bool | None = None
    evidence_commit: str = ""
    evidence_remote_verified: bool = False
    details: dict[str, Any] = field(default_factory=dict)
