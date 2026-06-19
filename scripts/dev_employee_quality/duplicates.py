from __future__ import annotations

import ast
import json
from collections import defaultdict

from .models import Finding, SourceFile


SCRIPT_SUFFIXES = {".ts", ".tsx", ".js", ".mjs", ".cjs"}


def _duplicate_findings(path: str, names: list[tuple[str, int]]) -> list[Finding]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for name, line in names:
        grouped[name].append(line)
    return [
        Finding(
            "duplicate_symbol",
            path,
            lines[1],
            f"top-level symbol {name} is defined more than once",
            ",".join(map(str, lines)),
        )
        for name, lines in sorted(grouped.items())
        if len(lines) > 1
    ]


def scan_python(source: SourceFile) -> list[Finding]:
    try:
        tree = ast.parse(source.text, filename=source.relative_path)
    except SyntaxError as exc:
        return [Finding("python_syntax", source.relative_path, exc.lineno or 1, str(exc))]
    names = [
        (node.name, node.lineno)
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    return _duplicate_findings(source.relative_path, names)


def _shell_top_level_name(line: str) -> str | None:
    if line != line.lstrip():
        return None
    stripped = line.strip()
    if stripped.startswith("function ") and stripped.endswith("{"):
        return stripped[len("function "):].split("(", 1)[0].strip()
    if stripped.endswith("() {"):
        return stripped.split("(", 1)[0].strip()
    return None


def _script_top_level_name(line: str) -> str | None:
    if line != line.lstrip():
        return None
    stripped = line.strip()
    if stripped.startswith("export "):
        stripped = stripped[len("export "):].lstrip()
    if stripped.startswith("default "):
        stripped = stripped[len("default "):].lstrip()
    for prefix in ("async function ", "function ", "class ", "const ", "let ", "var "):
        if stripped.startswith(prefix):
            remainder = stripped[len(prefix):]
            candidate = remainder.split("(", 1)[0].split("=", 1)[0].split(" ", 1)[0].strip()
            return candidate or None
    return None


def scan_text_symbols(source: SourceFile) -> list[Finding]:
    names: list[tuple[str, int]] = []
    for line_number, line in enumerate(source.text.splitlines(), 1):
        name = _shell_top_level_name(line) if source.suffix == ".sh" else _script_top_level_name(line)
        if name:
            names.append((name, line_number))
    return _duplicate_findings(source.relative_path, names)


def scan_json(source: SourceFile) -> list[Finding]:
    duplicates: list[str] = []

    def collect(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    try:
        json.loads(source.text, object_pairs_hook=collect)
    except json.JSONDecodeError as exc:
        return [Finding("json_syntax", source.relative_path, exc.lineno, exc.msg)]
    return [
        Finding("duplicate_json_key", source.relative_path, 1, f"JSON key {key} appears more than once", key)
        for key in sorted(set(duplicates))
    ]
