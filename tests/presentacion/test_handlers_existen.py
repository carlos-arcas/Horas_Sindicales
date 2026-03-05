from __future__ import annotations

import ast
from pathlib import Path


def _funciones(path: str) -> set[str]:
    module = ast.parse(Path(path).read_text(encoding="utf-8"))
    return {node.name for node in module.body if isinstance(node, ast.FunctionDef)}


def test_handlers_requeridos_existen() -> None:
    funciones_form = _funciones("app/ui/vistas/main_window/form_handlers.py")
    funciones_personas = _funciones("app/ui/vistas/main_window/acciones_personas.py")

    assert "on_completo_changed" in funciones_form
    assert "on_open_saldos_modal" in funciones_personas
