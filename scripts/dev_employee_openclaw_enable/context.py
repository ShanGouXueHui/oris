from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from .models import RuntimeContext


TASK_PATH = Path("memory/dev_employee/current_task.json")
REGISTRY_PATH = Path("orchestration/project_registry.json")
ACCEPTANCE_PATH = Path("config/dev_employee/openclaw_readonly_acceptance.json")


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def discover_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _latest_ready_evidence(evidence_directory: Path) -> Path:
    candidates = sorted(evidence_directory.glob("*.json"), reverse=True)
    for path in candidates:
        try:
            payload = _load_json(path)
        except Exception:
            continue
        if payload.get("result") == "READY":
            return path
    raise RuntimeError("no READY read-only readiness evidence found")


def _resolve_profile_expansion(acceptance: dict, task: dict) -> tuple[str, ...]:
    profile = str(acceptance["tool_policy"]["required_profile"])
    runtime_version = str(task["platform_state"]["openclaw_version"]).split()[0]
    expansions = acceptance["tool_policy"]["profile_expansions"]
    version_rules = expansions.get(runtime_version)
    if not isinstance(version_rules, dict):
        raise RuntimeError(f"no tool profile expansion for OpenClaw {runtime_version}")
    values = version_rules.get(profile)
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise RuntimeError(f"invalid tool profile expansion for {profile}")
    return tuple(values)


def load_context() -> RuntimeContext:
    repo_root = discover_repo_root()
    task = _load_json(repo_root / TASK_PATH)
    registry = _load_json(repo_root / REGISTRY_PATH)
    acceptance = _load_json(repo_root / ACCEPTANCE_PATH)
    if acceptance.get("schema_version") != 2:
        raise RuntimeError("unsupported automatic acceptance configuration schema")

    projects = registry.get("projects")
    if not isinstance(projects, dict):
        raise RuntimeError("project registry has no projects map")
    product_key = acceptance.get("baseline_project_key")
    product = projects.get(product_key)
    if not isinstance(product, dict):
        raise RuntimeError("baseline project is missing from project registry")

    architecture = task.get("architecture_decision")
    platform = task.get("platform_state")
    plugin = task.get("installed_plugin_state")
    if not all(isinstance(value, dict) for value in (architecture, platform, plugin)):
        raise RuntimeError("current task is missing architecture, platform, or plugin state")

    gateway_url = str(architecture["openclaw_local_gateway"]).rstrip("/")
    parsed_gateway = urlparse(gateway_url)
    expected_gateway_port = int(platform["openclaw_gateway_port"])
    if parsed_gateway.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("OpenClaw gateway is not loopback-scoped")
    if parsed_gateway.port != expected_gateway_port:
        raise RuntimeError("OpenClaw gateway URL and platform port disagree")

    approved_tools = tuple(plugin.get("runtime_tools") or ())
    required_hooks = tuple(plugin.get("runtime_hooks") or ())
    if len(approved_tools) != 3 or len(required_hooks) != 3:
        raise RuntimeError("current task does not define the exact approved tool and hook sets")

    agent_acceptance = acceptance["agent_acceptance"]
    turns = agent_acceptance["turns"]
    if not isinstance(turns, list) or len(turns) != len(approved_tools):
        raise RuntimeError("automatic acceptance turns do not match approved tool count")
    expected_turn_tools = {
        str(item.get("expected_tool"))
        for item in turns
        if isinstance(item, dict)
    }
    if expected_turn_tools != set(approved_tools):
        raise RuntimeError("automatic acceptance tool names do not match current task")

    telemetry_path = Path(
        str(plugin.get("telemetry_path") or acceptance["telemetry"]["default_path"])
    ).expanduser()
    marker_file = Path(str(plugin["private_marker"])).expanduser()
    openclaw_config = Path(str(acceptance["openclaw_config_path"])).expanduser()
    backup_root = Path(str(acceptance["backup_root"])).expanduser()
    evidence_directory = repo_root / str(acceptance["evidence"]["directory"])
    readiness_directory = repo_root / str(acceptance["readiness_evidence_directory"])
    public_routes = acceptance["public_routes"]
    tool_policy = acceptance["tool_policy"]

    return RuntimeContext(
        repo_root=repo_root,
        task_id=str(task["task_id"]),
        product_repo=Path(str(product["local_path"])).expanduser(),
        expected_product_commit=str(platform["product_baseline_commit"]),
        openclaw_config=openclaw_config,
        backup_root=backup_root,
        gateway_service=str(acceptance["gateway_service"]),
        gateway_url=gateway_url,
        public_url=str(architecture["primary_public_entry"]).rstrip("/"),
        public_root_route=str(public_routes["root"]),
        restricted_routes=tuple(str(item) for item in public_routes["restricted"]),
        plugin_id=str(plugin["plugin_id"]),
        plugin_version=str(plugin["version"]),
        approved_tools=approved_tools,
        required_hooks=required_hooks,
        marker_file=marker_file,
        internal_ports=(int(platform["enqueue_status_port"]), int(platform["intake_port"])),
        required_profile=str(tool_policy["required_profile"]),
        profile_expansion=_resolve_profile_expansion(acceptance, task),
        safe_probe_candidates=tuple(tool_policy["safe_builtin_probe_candidates"]),
        direct_probe_session_key=str(tool_policy["direct_probe_session_key"]),
        session_prefix=str(agent_acceptance["session_prefix"]),
        require_gateway_transport=bool(agent_acceptance["require_gateway_transport"]),
        require_persisted_native_session=bool(agent_acceptance["require_persisted_native_session"]),
        acceptance_turns=tuple(dict(item) for item in turns),
        turn_timeout_seconds=int(agent_acceptance["turn_timeout_seconds"]),
        telemetry_wait_seconds=int(agent_acceptance["telemetry_wait_seconds"]),
        telemetry_path=telemetry_path,
        evidence_directory=evidence_directory,
        evidence_commit_prefix=str(acceptance["evidence"]["commit_message_prefix"]),
        readiness_evidence=_latest_ready_evidence(readiness_directory),
    )
