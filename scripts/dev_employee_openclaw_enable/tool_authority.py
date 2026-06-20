from __future__ import annotations


WRITE_CAPABLE_CORE_TOOLS = frozenset(
    {
        "write",
        "edit",
        "apply_patch",
        "exec",
        "process",
        "code_execution",
    }
)


def is_write_capable_tool(name: str) -> bool:
    return name in WRITE_CAPABLE_CORE_TOOLS
