from __future__ import annotations

import ast
import importlib
import logging
import sys
import types
from pathlib import Path

import pytest

RUTA_STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")
MODULO_STATE_CONTROLLER = "app.ui.vistas.main_window.state_controller"
IMPORTS_CRITICOS = {
    ".state_helpers",
    ".state_actions",
    ".state_validations",
    ".state_bindings",
}


class _QtConst:
    def __getattr__(self, _name: str) -> int:
        return 0


class _QtDummyModule(types.ModuleType):
    def __getattr__(self, name: str):
        if name == "Qt":
            return _QtConst()
        return type(name, (), {})


@pytest.fixture
def entorno_qt_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    pyside = types.ModuleType("PySide6")
    qt_widgets = _QtDummyModule("PySide6.QtWidgets")
    qt_core = _QtDummyModule("PySide6.QtCore")
    qt_gui = _QtDummyModule("PySide6.QtGui")
    qt_print = _QtDummyModule("PySide6.QtPrintSupport")
    qt_charts = _QtDummyModule("PySide6.QtCharts")

    qt_core.Signal = lambda *args, **kwargs: object()
    qt_core.Slot = lambda *args, **kwargs: (lambda fn: fn)

    pyside.QtWidgets = qt_widgets
    pyside.QtCore = qt_core
    pyside.QtGui = qt_gui
    pyside.QtPrintSupport = qt_print
    pyside.QtCharts = qt_charts

    monkeypatch.setitem(sys.modules, "PySide6", pyside)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qt_widgets)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qt_core)
    monkeypatch.setitem(sys.modules, "PySide6.QtGui", qt_gui)
    monkeypatch.setitem(sys.modules, "PySide6.QtPrintSupport", qt_print)
    monkeypatch.setitem(sys.modules, "PySide6.QtCharts", qt_charts)


def _recargar_state_controller() -> object:
    sys.modules.pop(MODULO_STATE_CONTROLLER, None)
    return importlib.import_module(MODULO_STATE_CONTROLLER)


@pytest.mark.headless_safe
def test_state_controller_falla_rapido_si_falla_import_critico(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    entorno_qt_stub: None,
) -> None:
    importlib.invalidate_caches()
    original_import_module = importlib.import_module

    def _import_module_fallando(name: str, package: str | None = None):
        if name == ".state_helpers" and package == "app.ui.vistas.main_window":
            raise ImportError("fallo intencional state_helpers")
        return original_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", _import_module_fallando)
    caplog.set_level(logging.ERROR)

    with pytest.raises(
        RuntimeError,
        match=r"módulo crítico de MainWindow \.state_helpers",
    ):
        _recargar_state_controller()

    assert "MAINWINDOW_CRITICAL_UI_IMPORT_FAILED" in caplog.text
    assert "fallo intencional state_helpers" in caplog.text


@pytest.mark.headless_safe
def test_state_controller_importa_dependencias_criticas_sin_fallbacks_silenciosos() -> (
    None
):
    contenido = RUTA_STATE_CONTROLLER.read_text(encoding="utf-8")
    tree = ast.parse(contenido)
    try_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]

    for node in try_nodes:
        bloque = ast.get_source_segment(contenido, node) or ""
        assert "from .state_helpers import" not in bloque
        assert "from .state_actions import" not in bloque
        assert "from .state_validations import" not in bloque
        assert "from .state_bindings import" not in bloque

    for modulo in IMPORTS_CRITICOS:
        assert f'"{modulo}"' in contenido
    assert "MAINWINDOW_CRITICAL_UI_IMPORT_FAILED" in contenido


@pytest.mark.headless_safe
def test_state_controller_import_normal_sigue_operativo(
    entorno_qt_stub: None,
) -> None:
    modulo = _recargar_state_controller()

    assert hasattr(modulo, "MainWindow")
    assert hasattr(modulo, "registrar_state_bindings")
