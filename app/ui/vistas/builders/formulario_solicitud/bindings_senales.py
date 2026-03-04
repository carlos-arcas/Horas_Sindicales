from __future__ import annotations

from app.ui.vistas.main_window.wiring_helpers import conectar_signal

CONTEXTO_FORMULARIO_SOLICITUD = "builders_formulario_solicitud:create_formulario_solicitud"


def conectar_accion(window: object, signal: object, handler_name: str) -> None:
    conectar_signal(window, signal, handler_name, contexto=CONTEXTO_FORMULARIO_SOLICITUD)
