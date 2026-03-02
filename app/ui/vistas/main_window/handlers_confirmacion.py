from __future__ import annotations

import logging
from typing import Any

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text
from app.ui.vistas.main_window.importaciones import on_confirmar, toast_error


logger = logging.getLogger(__name__)


class HandlersConfirmacion:
    def __init__(self, window: Any) -> None:
        self._window = window

    def on_confirmar(self) -> None:
        try:
            persona_actual = self._window._current_persona()
            if persona_actual is None:
                self._window.toast.warning(
                    copy_text("ui.sync.delegada_no_seleccionada"),
                    title=copy_text("ui.validacion.validacion"),
                )
                return
            if not callable(on_confirmar):
                self._notify_handler_no_disponible()
                return
            on_confirmar(self._window)
        except Exception as exc:
            self._notify_handler_error(exc)

    def _notify_handler_no_disponible(self) -> None:
        mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
        detalle = copy_text("ui.errores.reintenta_contacta_soporte")
        toast_error(self._window.toast, f"{mensaje}. {detalle}")
        log_operational_error(
            logger,
            "UI_CONFIRMAR_HANDLER_NO_DISPONIBLE",
            extra={"handler": "on_confirmar", "contexto": "mainwindow._on_confirmar"},
        )

    def _notify_handler_error(self, exc: Exception) -> None:
        mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
        detalle = copy_text("ui.errores.reintenta_contacta_soporte")
        toast_error(self._window.toast, f"{mensaje}. {detalle}")
        log_operational_error(
            logger,
            "UI_CONFIRMAR_HANDLER_FALLO",
            exc=exc,
            extra={"handler": "on_confirmar", "contexto": "mainwindow._on_confirmar"},
        )
