from __future__ import annotations

import ast
from pathlib import Path


def test_mainwindow_expone_prompt_confirm_pdf_path() -> None:
    module = ast.parse(Path("app/ui/vistas/main_window/acciones_mixin.py").read_text(encoding="utf-8"))
    clase = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "AccionesMainWindowMixin")
    metodos = {node.name for node in clase.body if isinstance(node, ast.FunctionDef)}
    assert "_prompt_confirm_pdf_path" in metodos
