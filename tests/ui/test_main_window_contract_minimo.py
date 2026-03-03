from __future__ import annotations

import importlib
import sys
import types

import pytest


class _QtConst:
    def __getattr__(self, _name: str) -> int:
        return 0


class _QtDummyModule(types.ModuleType):
    def __getattr__(self, name: str):
        if name == "Qt":
            return _QtConst()
        return type(name, (), {})


def _crear_stub_pyside() -> tuple[types.ModuleType, _QtDummyModule, _QtDummyModule, _QtDummyModule, _QtDummyModule, _QtDummyModule]:
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

    return pyside, qt_widgets, qt_core, qt_gui, qt_print, qt_charts


@pytest.fixture
def modulos_main_window(monkeypatch: pytest.MonkeyPatch):
    pyside, qt_widgets, qt_core, qt_gui, qt_print, qt_charts = _crear_stub_pyside()

    monkeypatch.setitem(sys.modules, "PySide6", pyside)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qt_widgets)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qt_core)
    monkeypatch.setitem(sys.modules, "PySide6.QtGui", qt_gui)
    monkeypatch.setitem(sys.modules, "PySide6.QtPrintSupport", qt_print)
    monkeypatch.setitem(sys.modules, "PySide6.QtCharts", qt_charts)

    dto_mod = importlib.import_module("app.application.dto")
    state_controller = importlib.import_module("app.ui.vistas.main_window.state_controller")
    form_handlers = importlib.import_module("app.ui.vistas.main_window.form_handlers")

    yield dto_mod, state_controller.MainWindow, form_handlers

    for modulo in [
        "app.ui.vistas.main_window.state_controller",
        "app.ui.vistas.main_window.form_handlers",
    ]:
        sys.modules.pop(modulo, None)



class _FechaInvalidaStub:
    def isValid(self) -> bool:  # noqa: N802
        return False


class _FechaInputStub:
    def date(self) -> _FechaInvalidaStub:
        return _FechaInvalidaStub()


def test_main_window_contrato_minimo_metodos_no_lanzan(monkeypatch, modulos_main_window) -> None:
    dto_mod, main_window_cls, form_handlers = modulos_main_window
    window = main_window_cls.__new__(main_window_cls)
    window.fecha_input = _FechaInputStub()

    monkeypatch.setattr(form_handlers, "build_preview_solicitud", lambda _window: None)

    assert hasattr(window, "_apply_help_preferences")
    assert hasattr(window, "_build_preview_solicitud")
    assert hasattr(window, "_current_saldo_filtro")

    window._apply_help_preferences()
    assert window._build_preview_solicitud() is None
    assert isinstance(window._current_saldo_filtro(), dto_mod.PeriodoFiltro)
