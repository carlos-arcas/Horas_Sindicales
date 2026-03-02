from __future__ import annotations

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


def _instalar_stub_pyside() -> None:
    pyside = types.ModuleType("PySide6")
    qt_widgets = _QtDummyModule("PySide6.QtWidgets")
    qt_core = _QtDummyModule("PySide6.QtCore")
    qt_gui = _QtDummyModule("PySide6.QtGui")

    qt_core.Signal = lambda *args, **kwargs: object()
    qt_core.Slot = lambda *args, **kwargs: (lambda fn: fn)

    pyside.QtWidgets = qt_widgets
    pyside.QtCore = qt_core
    pyside.QtGui = qt_gui

    sys.modules["PySide6"] = pyside
    sys.modules["PySide6.QtWidgets"] = qt_widgets
    sys.modules["PySide6.QtCore"] = qt_core
    sys.modules["PySide6.QtGui"] = qt_gui


_instalar_stub_pyside()

from app.ui.vistas.main_window import utilidades_controlador_estado as estado_utils

pytestmark = pytest.mark.headless_safe


class _FakeI18n:
    def t(self, key: str, fallback: str = "") -> str:
        if key == "ui.placeholder_hora_hhmm":
            return "HH:MM"
        return fallback


class _FakeLineEdit:
    def __init__(self) -> None:
        self.placeholder = None

    def setPlaceholderText(self, text: str) -> None:
        self.placeholder = text


class _FakeTimeInput:
    def __init__(self) -> None:
        self._line_edit = _FakeLineEdit()

    def lineEdit(self) -> _FakeLineEdit:
        return self._line_edit


class _FakeWindow:
    def __init__(self) -> None:
        self._i18n = _FakeI18n()
        self.desde_input = _FakeTimeInput()
        self.hasta_input = _FakeTimeInput()


def test_configure_time_placeholders_resuelve_desde_i18n_sin_excepcion(monkeypatch: pytest.MonkeyPatch) -> None:
    window = _FakeWindow()
    monkeypatch.setattr(estado_utils.handlers_layout, "configure_time_placeholders", lambda _window: None)

    estado_utils.configure_time_placeholders(window)

    assert window.desde_input.lineEdit().placeholder == "HH:MM"
    assert window.hasta_input.lineEdit().placeholder == "HH:MM"
