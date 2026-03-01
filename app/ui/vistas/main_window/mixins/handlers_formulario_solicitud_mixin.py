from __future__ import annotations

import logging

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text

logger = logging.getLogger(__name__)


class HandlersFormularioSolicitudMixin:
    def _manejar_error_handler(self, codigo: str, exc: Exception | None = None) -> None:
        mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
        if hasattr(self, "toast") and getattr(self.toast, "error", None):
            self.toast.error(mensaje)
        log_operational_error(logger, codigo, exc=exc, extra={"contexto": self.__class__.__name__})

    def _on_fecha_changed(self, *args) -> None:
        _ = args
        try:
            self._update_solicitud_preview()
        except Exception as exc:
            self._manejar_error_handler("UI_ON_FECHA_CHANGED_FAILED", exc)

    def _update_solicitud_preview(self, *args) -> None:
        _ = args
        try:
            actualizar_estado = getattr(self, "_update_action_state", None)
            if callable(actualizar_estado):
                actualizar_estado()
            scheduler = getattr(self, "_schedule_preventive_validation", None)
            if callable(scheduler):
                scheduler()
        except Exception as exc:
            self._manejar_error_handler("UI_UPDATE_SOLICITUD_PREVIEW_FAILED", exc)

    def _on_completo_changed(self, *args) -> None:
        _ = args
        try:
            self._update_solicitud_preview()
        except Exception as exc:
            self._manejar_error_handler("UI_ON_COMPLETO_CHANGED_FAILED", exc)

    def _on_add_pendiente(self, *args) -> None:
        _ = args
        try:
            controller = getattr(self, "_solicitudes_controller", None)
            handler = getattr(controller, "on_add_pendiente", None)
            if callable(handler):
                handler()
                return
            boton = getattr(self, "agregar_button", None)
            if boton is not None and getattr(boton, "isEnabled", lambda: False)():
                boton.click()
        except Exception as exc:
            self._manejar_error_handler("UI_ON_ADD_PENDIENTE_FAILED", exc)

    def _on_confirmar(self, *args) -> None:
        _ = args
        try:
            controller = getattr(self, "_solicitudes_controller", None)
            handler = getattr(controller, "on_confirmar", None)
            if callable(handler):
                handler()
                return
            metodo_base = getattr(super(), "_on_confirmar", None)
            if callable(metodo_base):
                metodo_base()
                return
            self._manejar_error_handler("UI_CONFIRMAR_HANDLER_NO_DISPONIBLE")
        except Exception as exc:
            self._manejar_error_handler("UI_ON_CONFIRMAR_FAILED", exc)
