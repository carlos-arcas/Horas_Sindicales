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


def _crear_stub_pyside() -> tuple[
    types.ModuleType, types.ModuleType, types.ModuleType, types.ModuleType
]:
    pyside = types.ModuleType("PySide6")
    qt_widgets = _QtDummyModule("PySide6.QtWidgets")
    qt_core = _QtDummyModule("PySide6.QtCore")
    qt_gui = _QtDummyModule("PySide6.QtGui")

    qt_core.Signal = lambda *args, **kwargs: object()
    qt_core.Slot = lambda *args, **kwargs: (lambda fn: fn)

    pyside.QtWidgets = qt_widgets
    pyside.QtCore = qt_core
    pyside.QtGui = qt_gui
    return pyside, qt_widgets, qt_core, qt_gui


pytestmark = pytest.mark.headless_safe


@pytest.fixture
def estado_utils(monkeypatch: pytest.MonkeyPatch):
    pyside, qt_widgets, qt_core, qt_gui = _crear_stub_pyside()

    monkeypatch.setitem(sys.modules, "PySide6", pyside)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qt_widgets)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qt_core)
    monkeypatch.setitem(sys.modules, "PySide6.QtGui", qt_gui)

    modulo = importlib.import_module(
        "app.ui.vistas.main_window.utilidades_controlador_estado"
    )
    yield modulo
    importlib.invalidate_caches()
    sys.modules.pop("app.ui.vistas.main_window.utilidades_controlador_estado", None)


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


def test_configure_time_placeholders_resuelve_desde_i18n_sin_excepcion(
    monkeypatch: pytest.MonkeyPatch,
    estado_utils,
) -> None:
    window = _FakeWindow()
    monkeypatch.setattr(
        estado_utils.handlers_layout,
        "configure_time_placeholders",
        lambda _window: None,
    )

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


def test_update_conflicts_reminder_sin_i18n_sale_sin_error(estado_utils) -> None:
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


def test_warmup_sync_client_lanza_hilo_y_no_bloquea(
    monkeypatch: pytest.MonkeyPatch, estado_utils
) -> None:
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


def test_warmup_sync_client_es_idempotente(
    monkeypatch: pytest.MonkeyPatch, estado_utils
) -> None:
    service = _SyncServiceContador()
    window = _SyncWindow(service)

    monkeypatch.setattr(estado_utils.threading, "Thread", _ThreadEspia)

    estado_utils.warmup_sync_client(window, _FakeLogger())
    estado_utils.warmup_sync_client(window, _FakeLogger())

    assert _ThreadEspia.creations == 1
    assert _ThreadEspia.starts == 1


class _LoggerOperacionalFalso:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []


class _SyncServiceFallaSiempre:
    def ensure_connection(self) -> None:
        raise RuntimeError("boom")


def test_warmup_sync_client_loguea_error_operacional_si_falla(
    monkeypatch: pytest.MonkeyPatch,
    estado_utils,
) -> None:
    logger = _LoggerOperacionalFalso()
    window = _SyncWindow(_SyncServiceFallaSiempre())
    registros: list[dict[str, object]] = []

    monkeypatch.setattr(estado_utils.threading, "Thread", _ThreadEspia)

    def _fake_log_operational_error(logger_obj, code, *, exc, extra):
        registros.append(
            {"logger": logger_obj, "code": code, "exc": exc, "extra": extra}
        )

    monkeypatch.setattr(
        estado_utils, "log_operational_error", _fake_log_operational_error
    )

    estado_utils.warmup_sync_client(window, logger)

    assert callable(_ThreadEspia.last_target)

    _ThreadEspia.last_target()

    assert len(registros) == 1
    assert registros[0]["logger"] is logger
    assert registros[0]["code"] == "SYNC_WARMUP_FAILED"
    assert isinstance(registros[0]["exc"], RuntimeError)
    assert registros[0]["extra"] == {"operation": "sync_warmup"}


class _SyncServiceSinEnsure:
    pass


class _SyncServiceEnsureNoCallable:
    ensure_connection = 123


def test_warmup_sync_client_sin_ensure_connection_no_revienta(
    monkeypatch: pytest.MonkeyPatch,
    estado_utils,
) -> None:
    window_sin_ensure = _SyncWindow(_SyncServiceSinEnsure())
    window_no_callable = _SyncWindow(_SyncServiceEnsureNoCallable())

    monkeypatch.setattr(estado_utils.threading, "Thread", _ThreadEspia)

    estado_utils.warmup_sync_client(window_sin_ensure, _FakeLogger())
    estado_utils.warmup_sync_client(window_no_callable, _FakeLogger())

    assert _ThreadEspia.creations == 0
    assert _ThreadEspia.starts == 0
