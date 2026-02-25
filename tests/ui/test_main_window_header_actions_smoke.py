from __future__ import annotations

import sqlite3

import pytest

qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow

QApplication = qtwidgets.QApplication
QMessageBox = qtwidgets.QMessageBox


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


def test_sync_button_en_pagina_sincronizacion_no_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    window._switch_sidebar_page(0)
    if window.sync_button.isEnabled():
        window.sync_button.click()
        assert True
    else:
        assert "" != window.sync_button.toolTip()

    window.close()
    app.processEvents()


def test_nueva_solicitud_button_en_operativa_no_crash() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    window._switch_sidebar_page(1)
    if window.nueva_solicitud_button is not None and window.nueva_solicitud_button.isEnabled():
        window.nueva_solicitud_button.click()
        assert True
    else:
        assert window.nueva_solicitud_button is not None
        assert window.nueva_solicitud_button.toolTip() != ""

    window.close()
    app.processEvents()


def test_build_shell_layout_no_lanza_attribute_error() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    try:
        window._build_shell_layout()
    except AttributeError as exc:  # pragma: no cover - regresión explícita de wiring UI
        pytest.fail(f"_build_shell_layout lanzó AttributeError: {exc}")

    window.close()
    app.processEvents()
