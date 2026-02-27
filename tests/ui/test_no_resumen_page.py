from __future__ import annotations

import sqlite3

import pytest
from tests.ui.conftest import require_qt

qt = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = require_qt()
QPushButton = qt.QPushButton

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_navegacion_no_expone_resumen() -> None:
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

    sidebar_buttons = [button.text().strip().lower() for button in window.sidebar.findChildren(QPushButton)]
    assert all(texto != "resumen" for texto in sidebar_buttons)
    assert all("resumen" not in texto for texto in sidebar_buttons)
    assert all("resumen" not in button.objectName().strip().lower() for button in window.sidebar.findChildren(QPushButton))

    window.close()
    app.processEvents()
