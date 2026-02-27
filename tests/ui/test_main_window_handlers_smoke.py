from __future__ import annotations

import sqlite3

import pytest
from tests.ui.conftest import require_qt

QApplication = require_qt()
QMessageBox = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError).QMessageBox

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


def test_main_window_handlers_do_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.No)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    window._on_sync_with_confirmation()
    window._on_export_historico_pdf()
    window._clear_form()

    window.close()
    app.processEvents()
