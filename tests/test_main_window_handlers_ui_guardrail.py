from __future__ import annotations

import ast
from pathlib import Path

RUTA_ACCIONES_MIXIN = Path("app/ui/vistas/main_window/acciones_mixin.py")


def _resolver_metodo(nombre: str) -> ast.FunctionDef:
    tree = ast.parse(RUTA_ACCIONES_MIXIN.read_text(encoding="utf-8"), filename=str(RUTA_ACCIONES_MIXIN))
    clase = next(
        nodo for nodo in tree.body if isinstance(nodo, ast.ClassDef) and nodo.name == "AccionesMainWindowMixin"
    )
    return next(
        nodo for nodo in clase.body if isinstance(nodo, ast.FunctionDef) and nodo.name == nombre
    )


def test_verificar_handlers_ui_no_es_noop() -> None:
    metodo = _resolver_metodo("_verificar_handlers_ui")
    cuerpo = [
        nodo
        for nodo in metodo.body
        if not (
            isinstance(nodo, ast.Expr)
            and isinstance(getattr(nodo, "value", None), ast.Constant)
            and isinstance(nodo.value.value, str)
        )
    ]

    assert cuerpo, "_verificar_handlers_ui no debe estar vacío"
    assert not (
        len(cuerpo) == 1
        and isinstance(cuerpo[0], ast.Return)
        and isinstance(cuerpo[0].value, ast.Constant)
        and cuerpo[0].value.value is None
    ), "_verificar_handlers_ui no puede ser un no-op que devuelva None"
