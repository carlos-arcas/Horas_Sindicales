from __future__ import annotations

import logging
from typing import Any

from app.ui.copy_catalog import copy_text
from app.ui.vistas.main_window import acciones_pendientes


logger = logging.getLogger(__name__)


class HandlersFormulario:
    def __init__(self, window: Any) -> None:
        self._window = window

    def update_solicitud_preview(self) -> None:
        self._window._update_action_state()
        if hasattr(self._window, "_schedule_preventive_validation"):
            self._window._schedule_preventive_validation()

    def on_completo_changed(self, checked: bool) -> None:
        _ = checked
        self.update_solicitud_preview()

    def on_fecha_changed(self, nueva_fecha: Any) -> None:
        _ = nueva_fecha
        self.update_solicitud_preview()

    def on_add_pendiente(self) -> None:
        if hasattr(acciones_pendientes, "on_add_pendiente"):
            acciones_pendientes.on_add_pendiente(self._window)
            return
        for nombre in ("_on_agregar", "on_confirmar"):
            handler = getattr(self._window, nombre, None)
            if callable(handler):
                handler()
                return
        if hasattr(acciones_pendientes, "on_agregar"):
            acciones_pendientes.on_agregar(self._window)
            return
        boton = getattr(self._window, "agregar_button", None)
        if boton is not None and boton.isEnabled():
            boton.click()

    def configure_time_placeholders(self) -> None:
        for input_name in ("desde_input", "hasta_input"):
            input_widget = getattr(self._window, input_name, None)
            if input_widget is None:
                logger.warning(
                    "ui_handler_widget_missing",
                    extra={"handler": "configure_time_placeholders", "widget": input_name},
                )
                return
            if hasattr(input_widget, "setDisplayFormat"):
                input_widget.setDisplayFormat(copy_text("ui.solicitudes.formato_hora"))
            if hasattr(input_widget, "setToolTip"):
                input_widget.setToolTip(copy_text("ui.solicitudes.tooltip_formato_hora"))
