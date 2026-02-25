from __future__ import annotations

import sqlite3

import pytest

qt = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
Qt = qt.Qt
widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = widgets.QApplication
QFrame = widgets.QFrame
QLabel = widgets.QLabel

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


def _contiene_texto(widget: QFrame, texto: str) -> bool:
    return any(label.text() == texto for label in widget.findChildren(QLabel))


def test_pendientes_de_confirmar_esta_al_final_y_desplegado_en_solicitudes() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    window._switch_sidebar_page(1)

    assert window.solicitudes_splitter.orientation() == Qt.Orientation.Vertical
    assert window.solicitudes_splitter.count() == 2

    bloque_principal = window.solicitudes_splitter.widget(0)
    bloque_pendientes = window.solicitudes_splitter.widget(1)

    assert _contiene_texto(bloque_principal, "Alta de solicitud")
    assert _contiene_texto(bloque_pendientes, "Pendientes de confirmar")
    assert window.pending_details_button.isChecked() is True
    assert window.pending_details_content.isVisible() is True

    window.close()
    app.processEvents()


def test_historico_arranca_desplegado_al_abrir_solicitudes_incorporadas() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    window._switch_sidebar_page(2)

    assert window.historico_details_button.isChecked() is True
    assert window.historico_details_content.isVisible() is True

    window.close()
    app.processEvents()
