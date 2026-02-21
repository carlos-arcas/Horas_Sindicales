from __future__ import annotations

import sqlite3

import pytest

qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = qtwidgets.QApplication

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow
from app.ui.widgets.header import HeaderWidget


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


def test_content_area_has_no_internal_header_widget() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    content_headers = window.page_solicitudes.findChildren(HeaderWidget)
    assert content_headers == []

    window.close()
    app.processEvents()


def test_header_shell_actions_still_update_on_section_switch() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    window._update_header_for_section(2)
    assert window.header_title_label.text() == "Histórico"
    assert window.header_new_button.text() == "Nueva solicitud"

    window.header_new_button.setEnabled(True)
    window.header_new_button.click()
    app.processEvents()
    assert window._active_sidebar_index == 1

    called: list[bool] = []
    window._clear_form = lambda: called.append(True)
    window._update_header_for_section(1)
    assert window.header_title_label.text() == "Solicitudes"
    assert window.header_new_button.text() == "Limpiar formulario"

    window.header_new_button.setEnabled(True)
    window.header_new_button.click()
    app.processEvents()
    assert called == [True]

    window.close()
    app.processEvents()
