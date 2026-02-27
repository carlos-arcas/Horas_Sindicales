from __future__ import annotations

import sqlite3

import pytest
from tests.ui.conftest import require_qt

qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow

QApplication = require_qt()
QMessageBox = qtwidgets.QMessageBox
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


def test_main_window_smoke_instantiation_no_crash() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    assert window is not None

    window.close()
    app.processEvents()


def test_boton_sincronizar_en_pagina_sync_no_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    if window.sync_button.isEnabled():
        window.sync_button.click()
        assert True
    else:
        assert window.sync_button.toolTip() != ""

    window.close()
    app.processEvents()



def test_boton_exportar_historico_en_tab_existente() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    botones = window.main_tabs.widget(1).findChildren(QPushButton)
    textos = {boton.text() for boton in botones}
    assert any(texto.startswith("Exportar histórico PDF") for texto in textos)

    window.close()
    app.processEvents()
