from __future__ import annotations

import ast
import json
from collections import defaultdict

from .models import Finding, SourceFile


def _duplicate_findings(path: str, names: list[tuple[str, int]]) -> list[Finding]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for name, line in names:
        grouped[name].append(line)
    return [
        Finding("duplicate_symbol", path, lines[1], f"symbol {name} is defined more than once", ",".join(map(str, lines)))
        for name, lines in sorted(grouped.items())
        if len(lines) > 1
    ]


def scan_python(source: SourceFile) -> tuple[list[Finding], list[tuple[str, str, int]]]:
    try:
        tree = ast.parse(source.text, filename=source.relative_path)
    except SyntaxError as exc:
        return [Finding("python_syntax", source.relative_path, exc.lineno or 1, str(exc))], []
    names: list[tuple[str, int]] = []
    constants: list[tuple[str, str, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append((node.name, node.lineno))
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = ast.unparse(node.value) if node.value is not None else ""
            for target in targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    constants.append((target.id, value, node.lineno))
    return _duplicate_findings(source.relative_path, names), constants


def scan_text_symbols(source: SourceFile) -> tuple[list[Finding], list[tuple[str, str, int]]]:
    names: list[tuple[str, int]] = []
    constants: list[tuple[str, str, int]] = []
    for line_number, line in enumerate(source.text.splitlines(), 1):
        stripped = line.strip()
        if stripped.endswith("() {"):
            names.append((stripped.split("(", 1)[0].split()[-1], line_number))
        for prefix in ("function ", "class ", "const "):
            if stripped.startswith(prefix):
                names.append((stripped[len(prefix):].split("(", 1)[0].split()[0].rstrip("={"), line_number))
        if "=" in stripped and stripped.split("=", 1)[0].strip().isupper():
            name, value = stripped.split("=", 1)
            constants.append((name.strip(), value.strip(), line_number))
    return _duplicate_findings(source.relative_path, names), constants


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
    return [Finding("duplicate_json_key", source.relative_path, 1, f"JSON key {key} appears more than once", key) for key in sorted(set(duplicates))]
