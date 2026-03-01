from __future__ import annotations

import ast
from pathlib import Path

STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")
HISTORICO_ACTIONS = Path("app/ui/vistas/historico_actions.py")

WRAPPER_METHODS = {
    "_apply_historico_text_filter",
    "_historico_period_filter_state",
    "_update_historico_empty_state",
    "_on_historico_escape",
    "_selected_historico",
    "_selected_historico_solicitudes",
    "_on_historico_select_all_visible_toggled",
    "_sync_historico_select_all_visible_state",
    "_notify_historico_filter_if_hidden",
    "_on_export_historico_pdf",
    "_on_eliminar",
}

EXTRACTED_FUNCTIONS = {
    "apply_historico_text_filter",
    "historico_period_filter_state",
    "update_historico_empty_state",
    "on_historico_escape",
    "selected_historico",
    "selected_historico_solicitudes",
    "on_historico_select_all_visible_toggled",
    "sync_historico_select_all_visible_state",
    "notify_historico_filter_if_hidden",
    "on_export_historico_pdf",
    "on_eliminar",
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


def test_state_controller_historico_methods_are_wrappers() -> None:
    tree = _load_ast(STATE_CONTROLLER)
    class_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    methods = {node.name: node for node in class_node.body if isinstance(node, ast.FunctionDef)}

    for method_name in WRAPPER_METHODS:
        assert method_name in methods
        assert _is_wrapper_call(methods[method_name]), f"{method_name} debe ser wrapper de 1-3 líneas"


def test_historico_actions_define_extracted_entrypoints() -> None:
    tree = _load_ast(HISTORICO_ACTIONS)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    for expected in EXTRACTED_FUNCTIONS:
        assert expected in functions
