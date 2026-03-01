from __future__ import annotations

import ast
from pathlib import Path

STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")
PENDIENTES_ACTIONS = Path("app/ui/vistas/main_window/acciones_pendientes.py")

WRAPPER_METHODS = {
    "_selected_pending_row_indexes",
    "_selected_pending_for_editing",
    "_find_pending_row_by_id",
    "_focus_pending_row",
    "_focus_pending_by_id",
    "_on_review_hidden_pendientes",
    "_on_remove_huerfana",
    "_clear_pendientes",
    "_update_pending_totals",
    "_refresh_pending_conflicts",
    "_refresh_pending_ui_state",
}

EXTRACTED_FUNCTIONS = {
    "helper_selected_pending_row_indexes",
    "helper_selected_pending_for_editing",
    "helper_find_row_by_id",
    "helper_focus_pending_row",
    "helper_focus_pending_by_id",
    "on_review_hidden",
    "on_remove_huerfana",
    "on_clear_pendientes",
    "helper_update_pending_totals",
    "helper_refresh_pending_conflicts",
    "helper_refresh_pending_ui_state",
}


def _load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def _is_wrapper_call(method: ast.FunctionDef) -> bool:
    if len(method.body) > 3:
        return False
    terminal = method.body[-1]
    if not isinstance(terminal, ast.Return):
        return False
    call = terminal.value
    return isinstance(call, ast.Call) and isinstance(call.func, (ast.Name, ast.Attribute))


def test_state_controller_pendientes_methods_are_wrappers() -> None:
    tree = _load_ast(STATE_CONTROLLER)
    class_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    methods = {node.name: node for node in class_node.body if isinstance(node, ast.FunctionDef)}

    for method_name in WRAPPER_METHODS:
        assert method_name in methods
        assert _is_wrapper_call(methods[method_name]), f"{method_name} debe ser wrapper de 1-3 líneas"


def test_acciones_pendientes_define_extracted_entrypoints() -> None:
    tree = _load_ast(PENDIENTES_ACTIONS)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    for expected in EXTRACTED_FUNCTIONS:
        assert expected in functions
        assert expected.startswith(("on_", "helper_")), (
            "acciones_pendientes.py solo debe exponer nombres on_* / helper_* para esta extracción"
        )
