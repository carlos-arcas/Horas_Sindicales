from __future__ import annotations

import sqlite3

import pytest

qt = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = qt.QApplication
QComboBox = qt.QComboBox

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_main_window_tabs_and_delegada_selectors() -> None:
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

    tab_names = [window.main_tabs.tabText(i) for i in range(window.main_tabs.count())]
    assert "Solicitudes" in tab_names
    assert "Histórico" in tab_names
    assert "Configuración" in tab_names
    assert "Resumen" not in tab_names

    assert isinstance(window.findChild(QComboBox, "solicitudes_delegada_combo"), QComboBox)
    assert isinstance(window.historico_delegada_combo, QComboBox)

    window.close()
    app.processEvents()
