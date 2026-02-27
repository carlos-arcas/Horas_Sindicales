from __future__ import annotations

import sqlite3

from tests.ui.conftest import require_qt

QApplication = require_qt()

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_main_window_incluye_shell_sin_cabecera_global() -> None:
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
    assert window.sidebar is not None
    assert window.stacked_pages is not None
    assert window.statusBar() is not None
    assert getattr(window, "header_shell", None) is None
    window.close()
    app.processEvents()
