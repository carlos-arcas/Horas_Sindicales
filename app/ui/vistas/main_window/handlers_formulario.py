from __future__ import annotations

import logging

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text
from app.ui.vistas.main_window.importaciones import acciones_pendientes, on_confirmar, toast_error

logger = logging.getLogger(__name__)


class MainWindowHandlersFormularioMixin:
    def _on_fecha_changed(self, nueva_fecha) -> None:
        _ = nueva_fecha
        update_preview = getattr(self, "_update_solicitud_preview", None)
        if callable(update_preview):
            update_preview()

    def _update_solicitud_preview(self) -> None:
        self._update_action_state()
        schedule_validation = getattr(self, "_schedule_preventive_validation", None)
        if callable(schedule_validation):
            schedule_validation()

    def _on_completo_changed(self, checked: bool) -> None:
        is_completo = bool(checked)
        desde_container = getattr(self, "desde_container", None)
        hasta_container = getattr(self, "hasta_container", None)
        if desde_container is not None:
            desde_container.setVisible(not is_completo)
        if hasta_container is not None:
            hasta_container.setVisible(not is_completo)
        configure_placeholders = getattr(self, "_configure_time_placeholders", None)
        if callable(configure_placeholders):
            configure_placeholders()
        self._update_solicitud_preview()

    def _on_add_pendiente(self) -> None:
        if hasattr(acciones_pendientes, "on_add_pendiente"):
            acciones_pendientes.on_add_pendiente(self)
            return
        for nombre in ("_on_agregar", "on_confirmar"):
            handler = getattr(self, nombre, None)
            if callable(handler):
                handler()
                return
        if hasattr(acciones_pendientes, "on_agregar"):
            acciones_pendientes.on_agregar(self)
            return
        if getattr(self, "agregar_button", None) is not None and self.agregar_button.isEnabled():
            self.agregar_button.click()

    def _on_confirmar(self, *args, **kwargs) -> None:
        _ = (args, kwargs)
        try:
            persona_actual = self._current_persona()
            if persona_actual is None:
                self.toast.warning(
                    copy_text("ui.sync.delegada_no_seleccionada"),
                    title=copy_text("ui.validacion.validacion"),
                )
                return
            if not callable(on_confirmar):
                mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
                detalle = copy_text("ui.errores.reintenta_contacta_soporte")
                toast_error(self.toast, f"{mensaje}. {detalle}")
                log_operational_error(
                    logger,
                    "UI_CONFIRMAR_HANDLER_NO_DISPONIBLE",
                    extra={"handler": "on_confirmar", "contexto": "MainWindow._on_confirmar"},
                )
                return
            on_confirmar(self)
        except Exception as exc:
            mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
            detalle = copy_text("ui.errores.reintenta_contacta_soporte")
            toast_error(self.toast, f"{mensaje}. {detalle}")
            log_operational_error(
                logger,
                "UI_CONFIRMAR_HANDLER_FALLO",
                exc=exc,
                extra={"handler": "on_confirmar", "contexto": "MainWindow._on_confirmar"},
            )
