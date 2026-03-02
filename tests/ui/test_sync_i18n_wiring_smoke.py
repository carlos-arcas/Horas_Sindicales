from __future__ import annotations

import logging
import sqlite3

from tests.ui.conftest import require_qt

QApplication = require_qt()

from app.bootstrap.container import build_container
from app.ui.i18n_ui import ui_text
from app.ui.main_window import MainWindow


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def test_cambio_idioma_refresca_textos_sync_panel() -> None:
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
        servicio_i18n=container.servicio_i18n,
    )

    window.conflicts_reminder_label.setVisible(True)
    window.conflicts_reminder_label.setText(ui_text("ui.sync.panel.conflictos_pendientes", cantidad=2))
    base_estado = window.sync_panel_status.text()
    base_run = window.sync_status_label.text()
    base_conflictos = window.conflicts_reminder_label.text()

    window.cambiar_idioma("en")

    assert window.sync_panel_status.text() != base_estado
    assert window.sync_status_label.text() != base_run
    assert window.conflicts_reminder_label.text() != base_conflictos

    window.close()
    app.processEvents()


def test_missing_key_muestra_fallback_y_log_warning(caplog) -> None:
    caplog.set_level(logging.WARNING)

    texto = ui_text("ui.sync.panel.esta_key_no_existe")

    assert texto == "(texto no disponible)"
    assert any("i18n_missing_ui_key" in record.message for record in caplog.records)
