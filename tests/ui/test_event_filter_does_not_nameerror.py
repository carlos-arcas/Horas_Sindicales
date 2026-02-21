from __future__ import annotations

import sqlite3

import pytest

qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
qtcore = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
qtgui = pytest.importorskip("PySide6.QtGui", exc_type=ImportError)

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow

QApplication = qtwidgets.QApplication
QEvent = qtcore.QEvent
Qt = qtcore.Qt
QKeyEvent = qtgui.QKeyEvent


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_event_filter_handles_return_key_without_crash() -> None:
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

    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier)
    handled = window.eventFilter(window.notas_input, event)

    assert isinstance(handled, bool)

    window.close()
    app.processEvents()
