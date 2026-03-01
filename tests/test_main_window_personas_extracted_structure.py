from __future__ import annotations

import ast
from pathlib import Path

STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")
ACCIONES_PERSONAS = Path("app/ui/vistas/main_window/acciones_personas.py")

WRAPPER_METHODS = {
    "_is_form_dirty",
    "_confirmar_cambio_delegada",
    "_save_current_draft",
    "_restore_draft_for_persona",
    "_load_personas",
    "_current_persona",
    "_on_persona_changed",
    "_on_add_persona",
    "_on_edit_persona",
    "_on_delete_persona",
    "_sync_config_persona_actions",
    "_selected_config_persona",
    "_on_config_delegada_changed",
    "_restaurar_contexto_guardado",
}

EXTRACTED_FUNCTIONS = {
    "is_form_dirty",
    "confirmar_cambio_delegada",
    "save_current_draft",
    "restore_draft_for_persona",
    "load_personas",
    "current_persona",
    "on_persona_changed",
    "on_add_persona",
    "on_edit_persona",
    "on_delete_persona",
    "sync_config_persona_actions",
    "selected_config_persona",
    "on_config_delegada_changed",
    "restaurar_contexto_guardado",
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


def test_state_controller_personas_methods_are_wrappers() -> None:
    tree = _load_ast(STATE_CONTROLLER)
    class_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    methods = {node.name: node for node in class_node.body if isinstance(node, ast.FunctionDef)}

    for method_name in WRAPPER_METHODS:
        assert method_name in methods
        assert _is_wrapper_call(methods[method_name]), f"{method_name} debe ser wrapper de 1-3 líneas"


def test_acciones_personas_define_entrypoints() -> None:
    assert ACCIONES_PERSONAS.exists(), "Debe existir acciones_personas.py"
    tree = _load_ast(ACCIONES_PERSONAS)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    for expected in EXTRACTED_FUNCTIONS:
        assert expected in functions
