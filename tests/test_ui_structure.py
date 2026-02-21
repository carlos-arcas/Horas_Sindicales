from __future__ import annotations

import sqlite3

import pytest

qt = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = qt.QApplication
QScrollArea = qt.QScrollArea
QSplitter = qt.QSplitter

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


def test_main_window_instantiates() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    assert window.stacked_pages is not None
    assert window.sidebar is not None
    assert window.main_tabs is not None
    assert window.main_tabs.count() == 4

    window.close()
    app.processEvents()


def test_tabs_exist() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    tab_names = [window.main_tabs.tabText(index) for index in range(window.main_tabs.count())]
    assert "Operativa" in tab_names
    assert "Histórico" in tab_names
    assert "Configuración" in tab_names

    window.close()
    app.processEvents()


def test_splitter_present_in_solicitudes() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    window._switch_sidebar_page(1)
    splitter = window.main_tabs.widget(0).findChild(QSplitter, "solicitudesSplitter")
    assert splitter is not None
    assert splitter.count() == 2

    window.close()
    app.processEvents()


def test_configuracion_scroll_area() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    window._switch_sidebar_page(3)
    config_tab = window.main_tabs.widget(2)
    scroll_area = config_tab.findChild(QScrollArea)
    assert scroll_area is not None
    assert scroll_area.widgetResizable() is True

    window.close()
    app.processEvents()
