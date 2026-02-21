from __future__ import annotations

import ast
from pathlib import Path


REQUIRED_HANDLERS = {
    "_sincronizar_con_confirmacion",
    "_on_sync_with_confirmation",
    "_limpiar_formulario",
    "_clear_form",
    "_verificar_handlers_ui",
    "eventFilter",
}


def test_main_window_declara_handlers_criticos() -> None:
    source = Path("app/ui/vistas/main_window_vista.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    main_window = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    method_names = {item.name for item in main_window.body if isinstance(item, ast.FunctionDef)}
    assert REQUIRED_HANDLERS.issubset(method_names)
