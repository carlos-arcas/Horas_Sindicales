from __future__ import annotations

import ast

from tests.helpers_main_window_ast import resolver_metodo_main_window


def _get_method_node(method_name: str) -> ast.FunctionDef:
    encontrado = resolver_metodo_main_window(method_name)
    assert encontrado is not None, f"No se encontró {method_name} en MainWindow/mixins"
    return encontrado.nodo


def test_on_fecha_changed_tiene_firma_qdate() -> None:
    method = _get_method_node("_on_fecha_changed")
    assert len(method.args.args) == 2
    arg = method.args.args[1]
    assert arg.arg == "qdate"
    assert isinstance(arg.annotation, ast.Name)
    assert arg.annotation.id == "QDate"


def test_on_fecha_changed_actualiza_estado_y_refresca_preview() -> None:
    method = _get_method_node("_on_fecha_changed")
    body = method.body

    has_fecha_update = any(
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Attribute)
        and node.targets[0].attr == "_fecha_seleccionada"
        for node in body
    )
    assert has_fecha_update

    has_preview_call = any(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "_update_solicitud_preview"
        for node in body
    )
    assert has_preview_call

    has_super_delegate = any(
        isinstance(node, ast.Return)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "_on_fecha_changed"
        and isinstance(node.value.func.value, ast.Call)
        and isinstance(node.value.func.value.func, ast.Name)
        and node.value.func.value.func.id == "super"
        for node in body
    )
    assert has_super_delegate
