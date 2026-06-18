from __future__ import annotations

from .models import Finding, ScanPolicy, SourceFile


def _is_hex_identifier(value: str) -> bool:
    return len(value) == 40 and all(character in "0123456789abcdef" for character in value.lower())


def scan(source: SourceFile, policy: ScanPolicy) -> list[Finding]:
    if source.relative_path in policy.authoritative_literal_files:
        return []
    findings: list[Finding] = []
    endpoint_values = tuple(f"127.0.0.1:{port}" for port in policy.environment_ports)
    for line_number, line in enumerate(source.text.splitlines(), 1):
        stripped = line.strip()
        if "environment_loopback_port" in policy.detectors:
            for value in endpoint_values:
                if value in line:
                    findings.append(Finding("environment_loopback_port", source.relative_path, line_number, "derive endpoints from runtime configuration", value))
        if "public_oris_domain" in policy.detectors:
            for value in policy.public_domains:
                if value in line:
                    findings.append(Finding("public_oris_domain", source.relative_path, line_number, "derive public domains from deployment configuration", value))
        if "acceptance_project_name" in policy.detectors:
            for value in policy.acceptance_project_names:
                if value in line:
                    findings.append(Finding("acceptance_project_name", source.relative_path, line_number, "shared source must not embed acceptance project identities", value))
        if "absolute_host_path" in policy.detectors:
            for root_name in ("home", "root", "opt", "srv", "var"):
                marker = "/" + root_name + "/"
                if marker in line:
                    findings.append(Finding("absolute_host_path", source.relative_path, line_number, "derive host paths from registry or runtime context", marker))
        if "embedded_commit_sha" in policy.detectors:
            for token in stripped.replace('"', " ").replace("'", " ").replace("=", " ").split():
                candidate = token.strip(".,;:()[]{}")
                if _is_hex_identifier(candidate):
                    findings.append(Finding("embedded_commit_sha", source.relative_path, line_number, "discover commit identifiers from task metadata or evidence", candidate))
        if "embedded_commercial_task_id" in policy.detectors and "commercial-" in line and "20" in line:
            findings.append(Finding("embedded_commercial_task_id", source.relative_path, line_number, "read task identifiers from the current task descriptor"))
        if "forbidden_set_e" in policy.detectors and source.suffix == ".sh":
            parts = stripped.split()
            if len(parts) >= 2 and parts[0] == "set" and parts[1].startswith("-") and "e" in parts[1]:
                findings.append(Finding("forbidden_set_e", source.relative_path, line_number, "use explicit failure boundaries", stripped))
    return findings
