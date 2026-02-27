from __future__ import annotations

import sqlite3

import pytest
from tests.ui.conftest import require_qt

qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow

QApplication = require_qt()
QPushButton = qtwidgets.QPushButton


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


def test_historico_acciones_prioriza_exportar_y_sync_derecha() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    layout = window.historico_actions_layout
    assert layout.indexOf(window.eliminar_button) == 0
    assert layout.indexOf(window.generar_pdf_button) == 1

    sync_index = layout.indexOf(window.historico_sync_button)
    assert sync_index == layout.count() - 1
    assert layout.itemAt(sync_index - 1).spacerItem() is not None
    assert window.historico_sync_button.text() == "Sincronizar con Google Sheets"

    botones = window.main_tabs.widget(1).findChildren(QPushButton)
    textos = {boton.text() for boton in botones}
    assert "Ocultar filtros y listado" not in textos
    assert "Ver detalle" not in textos
    assert "Re-sincronizar" not in textos
    assert "Limpiar" not in textos

    assert (
        window.historico_export_hint_label.text()
        == "Para exportar, selecciona los registros que quieras exportar."
    )

    window.close()
    app.processEvents()
