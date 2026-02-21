from __future__ import annotations

import pytest

from app.entrypoints.ui_main import construir_mensaje_error_ui, manejar_excepcion_ui

QMessageBox = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError).QMessageBox


def test_ui_exception_message_contains_incident_id(monkeypatch) -> None:
    capturado: dict[str, str] = {}

    def _critical(_parent, _title, message):
        capturado["message"] = message
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", _critical)

    try:
        raise RuntimeError("fallo ui")
    except RuntimeError as exc:
        incident_id = manejar_excepcion_ui(RuntimeError, exc, exc.__traceback__)

    assert incident_id
    assert "ID de incidente:" in capturado["message"]


def test_construir_mensaje_error_ui_incluye_incidente() -> None:
    message = construir_mensaje_error_ui("INC-ABC123")

    assert "ID de incidente: INC-ABC123" in message
