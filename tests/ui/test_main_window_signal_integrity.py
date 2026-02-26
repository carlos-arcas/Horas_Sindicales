from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError).QApplication

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow


EXPECTED_HANDLERS = (
    "_on_sync_with_confirmation",
    "_clear_form",
    "_on_export_historico_pdf",
)


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def _connected_window_handlers() -> set[str]:
    source = Path("app/ui/vistas/builders/main_window_builders.py").read_text(encoding="utf-8")
    connect_targets = set(re.findall(r"connect\(window\.([A-Za-z_][A-Za-z0-9_]*)\)", source))
    action_targets = set(re.findall(r"addAction\([^\n]+window\.([A-Za-z_][A-Za-z0-9_]*)\)", source))
    return connect_targets | action_targets


def test_builder_connect_targets_exist_in_main_window() -> None:
    missing = [name for name in sorted(_connected_window_handlers()) if not hasattr(MainWindow, name)]
    assert missing == []


def test_main_window_build_has_required_handler_attributes() -> None:
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

    for handler_name in EXPECTED_HANDLERS:
        assert hasattr(window, handler_name)
        assert callable(getattr(window, handler_name))

    window.close()
    app.processEvents()
