from __future__ import annotations

import os
import sqlite3

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - depende de librerías Qt del entorno
    pytest.skip(f"PySide6 no disponible en entorno de test: {exc}", allow_module_level=True)

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_main_window_smoke_initialization() -> None:
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

    assert window.persona_combo is not None
    assert isinstance(window.isVisible(), bool)

    window.close()
    app.processEvents()
