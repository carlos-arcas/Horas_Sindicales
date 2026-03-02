from __future__ import annotations

import sys
import types


class _QtConst:
    def __getattr__(self, _name: str) -> int:
        return 0


class _QtDummyModule(types.ModuleType):
    def __getattr__(self, name: str):
        if name == "Qt":
            return _QtConst()
        return type(name, (), {})


def _instalar_stub_pyside() -> None:
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

    sys.modules["PySide6"] = pyside
    sys.modules["PySide6.QtWidgets"] = qt_widgets
    sys.modules["PySide6.QtCore"] = qt_core
    sys.modules["PySide6.QtGui"] = qt_gui
    sys.modules["PySide6.QtPrintSupport"] = qt_print
    sys.modules["PySide6.QtCharts"] = qt_charts


_instalar_stub_pyside()

from app.application.dto import PeriodoFiltro
from app.ui.vistas.main_window.state_controller import MainWindow
from app.ui.vistas.main_window import form_handlers


class _FechaInvalidaStub:
    def isValid(self) -> bool:  # noqa: N802
        return False


class _FechaInputStub:
    def date(self) -> _FechaInvalidaStub:
        return _FechaInvalidaStub()


def test_main_window_contrato_minimo_metodos_no_lanzan(monkeypatch) -> None:
    window = MainWindow.__new__(MainWindow)
    window.fecha_input = _FechaInputStub()

    monkeypatch.setattr(form_handlers, "build_preview_solicitud", lambda _window: None)

    assert hasattr(window, "_apply_help_preferences")
    assert hasattr(window, "_build_preview_solicitud")
    assert hasattr(window, "_current_saldo_filtro")

    window._apply_help_preferences()
    assert window._build_preview_solicitud() is None
    assert isinstance(window._current_saldo_filtro(), PeriodoFiltro)
