from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = PROJECT_ROOT / "app" / "ui"


def _imports_module(tree: ast.AST, module_name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == module_name or alias.name.startswith(f"{module_name}.") for alias in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == module_name or node.module.startswith(f"{module_name}."):
                return True
    return False


def test_ui_no_importa_sqlite3() -> None:
    violations: list[str] = []

    for py_file in sorted(UI_ROOT.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        if _imports_module(tree, "sqlite3"):
            violations.append(py_file.relative_to(PROJECT_ROOT).as_posix())

    assert not violations, "UI no debe importar sqlite3:\n" + "\n".join(violations)
