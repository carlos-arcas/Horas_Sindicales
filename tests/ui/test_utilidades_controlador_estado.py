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


class _FakeLogger:
    def __init__(self) -> None:
        self.exception_calls = 0

    def exception(self, _msg: str) -> None:
        self.exception_calls += 1


class _FakeReminderLabel:
    def __init__(self) -> None:
        self.visible = None
        self.text = None

    def setVisible(self, value: bool) -> None:
        self.visible = value

    def setText(self, value: str) -> None:
        self.text = value


class _WindowWithoutI18n:
    def __init__(self) -> None:
        self.conflicts_reminder_label = _FakeReminderLabel()


def test_update_conflicts_reminder_sin_i18n_sale_sin_error() -> None:
    logger = _FakeLogger()
    window = _WindowWithoutI18n()

    estado_utils.update_conflicts_reminder(window, logger)

    assert logger.exception_calls == 0


@pytest.fixture(autouse=True)
def _reset_thread_espia() -> None:
    _ThreadEspia.creations = 0
    _ThreadEspia.starts = 0
    _ThreadEspia.last_target = None
    _ThreadEspia.last_daemon = None


class _SyncServiceContador:
    def __init__(self) -> None:
        self.calls = 0

    def ensure_connection(self) -> None:
        self.calls += 1


class _SyncWindow:
    def __init__(self, service: object) -> None:
        self._sync_service = service


class _ThreadEspia:
    creations = 0
    starts = 0
    last_target = None
    last_daemon = None

    def __init__(self, *, target, daemon):
        _ThreadEspia.creations += 1
        _ThreadEspia.last_target = target
        _ThreadEspia.last_daemon = daemon

    def start(self) -> None:
        _ThreadEspia.starts += 1


def test_warmup_sync_client_lanza_hilo_y_no_bloquea(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _SyncServiceContador()
    window = _SyncWindow(service)

    monkeypatch.setattr(estado_utils.threading, "Thread", _ThreadEspia)

    estado_utils.warmup_sync_client(window, _FakeLogger())

    assert _ThreadEspia.creations == 1
    assert _ThreadEspia.starts == 1
    assert _ThreadEspia.last_daemon is True
    assert callable(_ThreadEspia.last_target)
    assert service.calls == 0

    _ThreadEspia.last_target()

    assert service.calls == 1


def test_warmup_sync_client_es_idempotente(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _SyncServiceContador()
    window = _SyncWindow(service)

    monkeypatch.setattr(estado_utils.threading, "Thread", _ThreadEspia)

    estado_utils.warmup_sync_client(window, _FakeLogger())
    estado_utils.warmup_sync_client(window, _FakeLogger())

    assert _ThreadEspia.creations == 1
    assert _ThreadEspia.starts == 1


class _SyncServiceSinEnsure:
    pass


class _SyncServiceEnsureNoCallable:
    ensure_connection = 123


def test_warmup_sync_client_sin_ensure_connection_no_revienta(monkeypatch: pytest.MonkeyPatch) -> None:
    window_sin_ensure = _SyncWindow(_SyncServiceSinEnsure())
    window_no_callable = _SyncWindow(_SyncServiceEnsureNoCallable())

    monkeypatch.setattr(estado_utils.threading, "Thread", _ThreadEspia)

    estado_utils.warmup_sync_client(window_sin_ensure, _FakeLogger())
    estado_utils.warmup_sync_client(window_no_callable, _FakeLogger())

    assert _ThreadEspia.creations == 0
    assert _ThreadEspia.starts == 0
