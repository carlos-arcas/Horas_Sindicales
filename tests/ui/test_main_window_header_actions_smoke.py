from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime

import pytest

qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow
from app.ui.vistas.main_window_vista import MainWindow as MainWindowVista

QApplication = qtwidgets.QApplication
QMessageBox = qtwidgets.QMessageBox


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def _build_window() -> MainWindowVista:
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


def test_main_window_header_buttons_click_do_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    assert window.header_sync_button is not None
    assert window.header_new_button is not None

    if window.header_sync_button.isEnabled():
        window.header_sync_button.click()
    else:
        assert window.header_sync_button.toolTip() != ""

    window.header_new_button.click()

    window.close()
    app.processEvents()


@dataclass
class _DummySolicitud:
    fecha: object | None = None
    fecha_solicitud: object | None = None
    fecha_inicio: object | None = None
    fecha_desde: object | None = None


@pytest.mark.parametrize(
    ("item", "esperada"),
    [
        (_DummySolicitud(fecha=date(2025, 1, 10)), date(2025, 1, 10)),
        (_DummySolicitud(fecha=datetime(2025, 1, 10, 8, 30)), date(2025, 1, 10)),
        (_DummySolicitud(fecha_solicitud="2025-01-10"), date(2025, 1, 10)),
        (_DummySolicitud(fecha_inicio="2025-01-10"), date(2025, 1, 10)),
        (_DummySolicitud(fecha_desde="2025-01-10"), date(2025, 1, 10)),
        (_DummySolicitud(fecha_solicitud="10/01/2025"), None),
        (_DummySolicitud(), None),
    ],
)
def test_extraer_fecha_solicitud_soporta_variantes(item: object, esperada: date | None) -> None:
    assert MainWindowVista._extraer_fecha_solicitud(item) == esperada
