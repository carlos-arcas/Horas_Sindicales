from __future__ import annotations

import ast
from pathlib import Path

STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")


def _get_method_node(method_name: str) -> ast.FunctionDef:
    tree = ast.parse(STATE_CONTROLLER.read_text(encoding="utf-8"))
    main_window = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    return next(node for node in main_window.body if isinstance(node, ast.FunctionDef) and node.name == method_name)


def test_on_fecha_changed_tiene_firma_qdate() -> None:
    method = _get_method_node("_on_fecha_changed")
    assert len(method.args.args) == 2
    arg = method.args.args[1]
    assert arg.arg == "qdate"
    assert isinstance(arg.annotation, ast.Name)
    assert arg.annotation.id == "QDate"


def test_on_fecha_changed_actualiza_estado_y_refresca_preview() -> None:
    method = _get_method_node("_on_fecha_changed")
    source = ast.get_source_segment(STATE_CONTROLLER.read_text(encoding="utf-8"), method) or ""

    assert "self._fecha_seleccionada" in source
    assert "_update_solicitud_preview" in source
