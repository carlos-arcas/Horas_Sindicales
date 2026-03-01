from __future__ import annotations

import ast
from pathlib import Path


STATE_CONTROLLER_PATH = Path("app/ui/vistas/main_window/state_controller.py")
REQUIRED_HANDLERS = ("_on_confirmar", "_normalize_input_heights")


def _main_window_method_names() -> set[str]:
    code = STATE_CONTROLLER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(code, filename=str(STATE_CONTROLLER_PATH))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow":
            return {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
    return set()


def test_mainwindow_define_handlers_requeridos_para_builders() -> None:
    handlers = _main_window_method_names()
    faltantes = [name for name in REQUIRED_HANDLERS if name not in handlers]
    assert not faltantes, f"MainWindow no define handlers requeridos: {', '.join(faltantes)}"
