from __future__ import annotations

import logging
from typing import Any

from .importaciones import acciones_pendientes

logger = logging.getLogger(__name__)


class HandlersFormulario:
    def __init__(self, window: Any) -> None:
        self._window = window

    def update_solicitud_preview(self) -> None:
        window = self._window
        window._update_action_state()
        if hasattr(window, "_schedule_preventive_validation"):
            window._schedule_preventive_validation()

    def on_completo_changed(self, checked: bool) -> None:
        _ = checked
        self.update_solicitud_preview()

    def on_fecha_changed(self, nueva_fecha: Any) -> None:
        _ = nueva_fecha
        self.update_solicitud_preview()

    def on_add_pendiente(self) -> None:
        window = self._window
        if hasattr(acciones_pendientes, "on_add_pendiente"):
            acciones_pendientes.on_add_pendiente(window)
            return
        for nombre in ("_on_agregar", "on_confirmar"):
            handler = getattr(window, nombre, None)
            if callable(handler):
                handler()
                return
        if hasattr(acciones_pendientes, "on_agregar"):
            acciones_pendientes.on_agregar(window)
            return
        if getattr(window, "agregar_button", None) is not None and window.agregar_button.isEnabled():
            window.agregar_button.click()
