from __future__ import annotations

import sqlite3

import pytest
from tests.ui.conftest import require_qt

qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = require_qt()
QPushButton = qtwidgets.QPushButton

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def _build_window() -> MainWindow:
    container = build_container(connection_factory=_in_memory_connection)
    return MainWindow(
        container.persona_use_cases,
        container.solicitud_use_cases,
        container.grupo_use_cases,
        container.sheets_service,
        container.sync_service,
        container.conflicts_service,
        health_check_use_case=None,
        alert_engine=container.alert_engine,
    )


def test_no_existe_cabecera_shell_global() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    assert window.findChild(qtwidgets.QWidget, "header_shell") is None

    window.close()
    app.processEvents()


def test_botones_header_eliminados_del_root() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    textos = {boton.text() for boton in window.findChildren(QPushButton)}
    assert "Sync" not in textos
    assert "Exportar" not in textos
    assert "Config" not in textos

    window.close()
    app.processEvents()
