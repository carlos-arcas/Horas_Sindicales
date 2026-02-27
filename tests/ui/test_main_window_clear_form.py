from __future__ import annotations

import sqlite3

import pytest
from tests.ui.conftest import require_qt

QApplication = require_qt()
QDate = pytest.importorskip("PySide6.QtCore", exc_type=ImportError).QDate
QTime = pytest.importorskip("PySide6.QtCore", exc_type=ImportError).QTime

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_main_window_clear_form_resets_ui_without_exceptions() -> None:
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

    window.notas_input.setPlainText("nota temporal")
    window.fecha_input.setDate(QDate(2024, 1, 15))
    window.desde_input.setTime(QTime(11, 30))
    window.hasta_input.setTime(QTime(12, 45))
    window.completo_check.setChecked(True)

    window._clear_form()

    assert window.notas_input.toPlainText() == ""
    assert window.completo_check.isChecked() is False

    window.close()
    app.processEvents()
