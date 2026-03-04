from __future__ import annotations

import importlib

import pytest


MODULOS_UI = (
    "app.ui.vistas.confirmacion_adaptador_qt",
    "app.ui.vistas.confirmacion_orquestacion",
    "app.ui.vistas.confirmacion_actions",
)


def test_imports_ui_confirmacion_sin_errores() -> None:
    pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    for modulo in MODULOS_UI:
        importlib.import_module(modulo)
