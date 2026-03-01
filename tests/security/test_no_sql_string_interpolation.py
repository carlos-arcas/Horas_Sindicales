from __future__ import annotations

import ast
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[2] / "app"
SQL_METHODS = {"execute", "executemany"}
ALLOWED_FILES = {
    Path("infrastructure/migrations.py"),
    Path("infrastructure/sqlite_connection_config.py"),
    Path("infrastructure/sqlite_uow.py"),
    Path("application/use_cases/sync_sheets/pull_runner.py"),
    Path("infrastructure/seed.py"),
}


def _is_sql_method_call(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr in SQL_METHODS


def _is_unsafe_sql_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return True
    return False


class _SqlInterpolationVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.assignments: dict[str, ast.AST] = {}
        self.violations: list[str] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            self.assignments[node.targets[0].id] = node.value
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if _is_sql_method_call(node) and node.args:
            sql_expr = node.args[0]
            if isinstance(sql_expr, ast.Name):
                if sql_expr.id.isupper():
                    self.generic_visit(node)
                    return
                sql_expr = self.assignments.get(sql_expr.id, sql_expr)
            if _is_unsafe_sql_expr(sql_expr):
                rel = self.file_path.relative_to(APP_DIR.parent)
                self.violations.append(f"{rel}:{node.lineno}")
        self.generic_visit(node)


def test_no_sql_interpolation_on_execute_calls() -> None:
    violations: list[str] = []

    for file_path in sorted(APP_DIR.rglob("*.py")):
        rel = file_path.relative_to(APP_DIR)
        if rel in ALLOWED_FILES:
            continue
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        visitor = _SqlInterpolationVisitor(file_path)
        visitor.visit(tree)
        violations.extend(visitor.violations)

    assert not violations, (
        "SQL debe ser literal + parámetros; evita interpolación."
        f" Hallazgos: {', '.join(violations)}"
    )
