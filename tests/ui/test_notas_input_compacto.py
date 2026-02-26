from __future__ import annotations

import sqlite3

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = QtWidgets.QApplication
QSizePolicy = QtWidgets.QSizePolicy

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_notas_input_usa_altura_compacta_sin_romper_layout() -> None:
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

    notas_input = getattr(window, "notas_input", None)

    assert notas_input is not None
    assert notas_input.maximumHeight() > 0
    assert notas_input.maximumHeight() <= 120
    assert notas_input.sizePolicy().verticalPolicy() != QSizePolicy.Expanding

    assert getattr(window, "agregar_button", None) is not None
    assert getattr(window, "pendientes_table", None) is not None

    window.close()
    app.processEvents()
