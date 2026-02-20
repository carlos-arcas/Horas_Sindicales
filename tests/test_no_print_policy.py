from __future__ import annotations

import ast
from pathlib import Path


def _iter_target_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []

    main_file = repo_root / "main.py"
    if main_file.exists():
        files.append(main_file)

    for rel in ("app", "app/entrypoints"):
        base = repo_root / rel
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if any(part in {".git", "venv", ".venv", "build", "dist", "__pycache__"} for part in path.parts):
                continue
            files.append(path)

    # Deduplicación y orden estable
    return sorted(set(files))


def _find_print_calls(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            lines.append(node.lineno)
    return sorted(lines)


def test_no_print_policy() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    # Whitelist mínima y explícita. Mantener vacía salvo caso inevitable y documentado.
    whitelist: dict[str, set[int]] = {}

    violations: list[str] = []
    for file_path in _iter_target_files(repo_root):
        rel_path = file_path.relative_to(repo_root).as_posix()
        for lineno in _find_print_calls(file_path):
            if lineno in whitelist.get(rel_path, set()):
                continue
            violations.append(f"{rel_path}:{lineno}")

    assert not violations, "Se detectaron usos prohibidos de print():\n" + "\n".join(violations)
