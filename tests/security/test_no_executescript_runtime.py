from __future__ import annotations

import ast
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[2] / "app"
ALLOWED_PATHS = {
    Path("infrastructure/migrations.py"),
    Path("infrastructure/migrations_cli.py"),
}


def _iter_python_files(root: Path):
    for file_path in sorted(root.rglob("*.py")):
        rel_path = file_path.relative_to(root)
        if rel_path in ALLOWED_PATHS:
            continue
        yield file_path


def test_no_executescript_outside_migrations() -> None:
    violations: list[str] = []

    for file_path in _iter_python_files(APP_DIR):
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr == "executescript":
                rel = file_path.relative_to(APP_DIR.parent)
                violations.append(f"{rel}:{node.lineno}")

    assert not violations, "executescript() solo se permite en migraciones: " + ", ".join(violations)
