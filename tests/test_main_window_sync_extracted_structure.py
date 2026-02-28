from __future__ import annotations

import ast
from pathlib import Path

STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")
ACCIONES_SYNC = Path("app/ui/vistas/main_window/acciones_sincronizacion.py")


def _load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def _method_sizes(class_node: ast.ClassDef) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef):
            sizes[node.name] = (node.end_lineno or node.lineno) - node.lineno + 1
    return sizes


def test_state_controller_sync_methods_are_extracted_or_wrapped() -> None:
    tree = _load_ast(STATE_CONTROLLER)
    class_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    sizes = _method_sizes(class_node)

    for method_name in ("_apply_sync_report", "_show_sync_details_dialog", "_on_sync_finished", "_on_sync_failed"):
        assert method_name in sizes
        assert sizes[method_name] <= 3, f"{method_name} debe ser wrapper de 1-3 líneas"


def test_acciones_sincronizacion_define_entrypoints() -> None:
    assert ACCIONES_SYNC.exists(), "Debe existir acciones_sincronizacion.py"
    tree = _load_ast(ACCIONES_SYNC)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    for expected in {"on_sync", "on_sync_finished", "apply_sync_report"}:
        assert expected in functions
