from __future__ import annotations

import sys
import types

from app.entrypoints.ui_main import construir_mensaje_error_ui, manejar_excepcion_ui


class _QApplicationFalso:
    @staticmethod
    def instance():
        return object()


class _QMessageBoxFalso:
    class StandardButton:
        Ok = 1

    ultimo_mensaje: str | None = None

    @classmethod
    def critical(cls, _parent, _title, message):
        cls.ultimo_mensaje = message
        return cls.StandardButton.Ok


def test_ui_exception_message_contains_incident_id(monkeypatch) -> None:
    modulo_qt_widgets_falso = types.SimpleNamespace(
        QApplication=_QApplicationFalso,
        QMessageBox=_QMessageBoxFalso,
    )
    modulo_qt_falso = types.SimpleNamespace(QtWidgets=modulo_qt_widgets_falso)
    monkeypatch.setitem(sys.modules, "PySide6", modulo_qt_falso)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", modulo_qt_widgets_falso)

    try:
        raise RuntimeError("fallo ui")
    except RuntimeError as exc:
        incident_id = manejar_excepcion_ui(RuntimeError, exc, exc.__traceback__)

    assert incident_id
    assert _QMessageBoxFalso.ultimo_mensaje is not None
    assert "ID de incidente:" in _QMessageBoxFalso.ultimo_mensaje


def test_construir_mensaje_error_ui_incluye_incidente() -> None:
    message = construir_mensaje_error_ui("INC-ABC123")

    assert "ID de incidente: INC-ABC123" in message
