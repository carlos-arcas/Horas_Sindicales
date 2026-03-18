from __future__ import annotations

import sqlite3

from tests.ui.conftest import require_qt

QApplication = require_qt()

from app.bootstrap.container import build_container
from app.ui.vistas.main_window import MainWindow


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_main_window_build_ui_smoke_no_exception() -> None:
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
        proveedor_ui_solo_lectura=container.proveedor_ui_solo_lectura,
    )

    window._build_ui()

    assert callable(getattr(window, "_on_sync_with_confirmation", None))
    assert callable(getattr(window, "_clear_form", None))
    assert callable(getattr(window, "_on_export_historico_pdf", None))
    assert hasattr(window, "fecha_input")
    assert hasattr(window, "pendientes_table")
    assert hasattr(window, "sync_button")
    assert callable(getattr(window, "_on_fecha_changed", None))
    assert window.fecha_input.receivers(window.fecha_input.dateChanged) > 0

    window.close()
    app.processEvents()
