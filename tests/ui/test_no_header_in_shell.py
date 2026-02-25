from __future__ import annotations

import sqlite3

import pytest

qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = qtwidgets.QApplication
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


def test_main_window_no_renderiza_header_global() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    assert window.findChild(qtwidgets.QWidget, "header_shell") is None

    root_buttons = {button.text() for button in window.findChildren(QPushButton)}
    assert "Sync" not in root_buttons
    assert "Exportar" not in root_buttons
    assert "Config" not in root_buttons

    window.close()
    app.processEvents()


def test_acciones_reubicadas_estan_disponibles() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    assert window.nueva_solicitud_button is not None
    assert window.nueva_solicitud_button.text() == "Nueva solicitud"

    window._switch_sidebar_page(2)
    assert window.exportar_historico_button is not None
    assert window.exportar_historico_button.text().startswith("Exportar histórico PDF")

    window._switch_sidebar_page(3)
    assert window.main_tabs.tabText(window.main_tabs.currentIndex()) == "Configuración"

    window._switch_sidebar_page(0)
    assert window.sync_button.text() == "Sincronizar ahora"

    window.close()
    app.processEvents()
