from __future__ import annotations

import sqlite3

import pytest
from tests.ui.conftest import require_qt

qt = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = require_qt()
QPushButton = qt.QPushButton
QStackedWidget = qt.QStackedWidget

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_main_window_layout_structure_sidebar_and_pages() -> None:
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

    assert isinstance(window.stacked_pages, QStackedWidget)
    assert window.stacked_pages.count() == 1

    sidebar_buttons = [button.text() for button in window.sidebar.findChildren(QPushButton)]
    assert sidebar_buttons[:3] == ["Solicitudes", "Histórico", "Configuración"]

    window.close()
    app.processEvents()
