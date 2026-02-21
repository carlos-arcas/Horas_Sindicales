from __future__ import annotations

import sqlite3

import pytest

qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
qtcore = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
qtgui = pytest.importorskip("PySide6.QtGui", exc_type=ImportError)

from app.bootstrap.container import build_container
import app.ui.vistas.main_window_vista as main_window_vista
from app.ui.main_window import MainWindow

QApplication = qtwidgets.QApplication
QEvent = qtcore.QEvent
Qt = qtcore.Qt
QKeyEvent = qtgui.QKeyEvent


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_event_filter_handles_keypress_without_crash_when_qkeyevent_symbol_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    container = build_container(connection_factory=_in_memory_connection)

    window = MainWindow(
        container.persona_use_cases,
        container.solicitud_use_cases,
        container.grupo_use_cases,
        container.sheets_service,
        container.sync_service,
        container.conflicts_service,
        health_check_use_case=None,
        alert_engine=container.alert_engine,
    )

    monkeypatch.setattr(main_window_vista, "QKeyEvent", None, raising=False)
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier)
    handled = window.eventFilter(window.notas_input, event)

    assert isinstance(handled, bool)

    window.close()
    app.processEvents()


def test_event_filter_ignores_keyrelease_without_nameerror() -> None:
    app = QApplication.instance() or QApplication([])
    container = build_container(connection_factory=_in_memory_connection)

    window = MainWindow(
        container.persona_use_cases,
        container.solicitud_use_cases,
        container.grupo_use_cases,
        container.sheets_service,
        container.sync_service,
        container.conflicts_service,
        health_check_use_case=None,
        alert_engine=container.alert_engine,
    )

    event = QKeyEvent(QEvent.Type.KeyRelease, Qt.Key_Return, Qt.NoModifier)
    handled = window.eventFilter(window.notas_input, event)

    assert isinstance(handled, bool)

    window.close()
    app.processEvents()
