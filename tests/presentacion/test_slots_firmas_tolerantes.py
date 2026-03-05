from __future__ import annotations

import ast
from pathlib import Path


def _get_method_node(path: str, class_name: str, method_name: str) -> ast.FunctionDef:
    module = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == method_name:
                    return child
    raise AssertionError(f"No se encontró {class_name}.{method_name}")


def test_on_pending_selection_changed_acepta_varargs() -> None:
    method = _get_method_node(
        "app/ui/vistas/main_window/acciones_mixin.py",
        "AccionesMainWindowMixin",
        "_on_pending_selection_changed",
    )
    assert method.args.vararg is not None


def test_update_solicitud_preview_acepta_varargs() -> None:
    method = _get_method_node(
        "app/ui/vistas/main_window/state_controller.py",
        "MainWindow",
        "_update_solicitud_preview",
    )
    assert method.args.vararg is not None
