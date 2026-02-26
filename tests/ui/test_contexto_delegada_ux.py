from __future__ import annotations

import sqlite3

import pytest

qt = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = qt.QApplication
QMessageBox = qt.QMessageBox

from app.application.dto import PersonaDTO
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


def test_sin_delegada_nueva_solicitud_bloqueada_con_tooltip() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    assert window.nueva_solicitud_button is not None
    assert window.nueva_solicitud_button.isEnabled() is False
    assert window.nueva_solicitud_button.toolTip() == "Selecciona delegada"

    window.close()
    app.processEvents()


def test_cambiar_delegada_con_formulario_sucio_pide_confirmacion(monkeypatch: pytest.MonkeyPatch) -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    p1 = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Ana"))
    p2 = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Bea"))
    window._load_personas(select_id=p1.id)
    window.notas_input.setPlainText("Borrador pendiente")

    llamadas: list[tuple[object, str, str]] = []

    def _fake_question(parent, title, text, *args, **kwargs):
        llamadas.append((parent, title, text))
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", _fake_question)

    window.persona_combo.setCurrentIndex(1)

    assert llamadas
    assert "descartará el formulario actual" in llamadas[0][2]
    assert window.persona_combo.currentData() == p1.id
    assert window.notas_input.toPlainText() == "Borrador pendiente"

    window.close()
    app.processEvents()
