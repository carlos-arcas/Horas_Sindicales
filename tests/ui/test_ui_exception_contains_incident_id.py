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


def test_manejar_excepcion_ui_avoids_reentrant_messagebox(monkeypatch) -> None:
    calls: list[str] = []

    def _critical(_parent, _title, _message):
        calls.append("called")
        raise RuntimeError("dialog failure")

    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", _critical)

    try:
        raise RuntimeError("fallo ui")
    except RuntimeError as exc:
        incident_id = manejar_excepcion_ui(RuntimeError, exc, exc.__traceback__)

    assert incident_id
    assert len(calls) == 1


def test_manejar_excepcion_ui_skips_dialog_when_already_showing(monkeypatch) -> None:
    monkeypatch.setattr("app.entrypoints.ui_main._SHOWING_FATAL_ERROR_DIALOG", True)

    def _critical(_parent, _title, _message):
        raise AssertionError("No debe mostrar diálogo durante reentrada")

    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", _critical)

    try:
        raise RuntimeError("fallo ui")
    except RuntimeError as exc:
        incident_id = manejar_excepcion_ui(RuntimeError, exc, exc.__traceback__)

    assert incident_id
