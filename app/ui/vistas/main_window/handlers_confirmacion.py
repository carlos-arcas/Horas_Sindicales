from __future__ import annotations

import logging
from typing import Any

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text

from .importaciones import toast_error

logger = logging.getLogger(__name__)


class HandlersConfirmacion:
    def __init__(self, window: Any) -> None:
        self._window = window

    def on_confirmar(self) -> None:
        window = self._window
        try:
            persona_actual = window._current_persona()
            if persona_actual is None:
                window.toast.warning(
                    copy_text("ui.sync.delegada_no_seleccionada"),
                    title=copy_text("ui.validacion.validacion"),
                )
                return
            confirmar_action = getattr(window, "_confirmar_action", None)
            if not callable(confirmar_action):
                mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
                detalle = copy_text("ui.errores.reintenta_contacta_soporte")
                toast_error(window.toast, f"{mensaje}. {detalle}")
                log_operational_error(
                    logger,
                    "UI_CONFIRMAR_HANDLER_NO_DISPONIBLE",
                    extra={"handler": "on_confirmar", "contexto": "mainwindow._on_confirmar"},
                )
                return
            confirmar_action(window)
        except Exception as exc:
            mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
            detalle = copy_text("ui.errores.reintenta_contacta_soporte")
            toast_error(window.toast, f"{mensaje}. {detalle}")
            log_operational_error(
                logger,
                "UI_CONFIRMAR_HANDLER_FALLO",
                exc=exc,
                extra={"handler": "on_confirmar", "contexto": "mainwindow._on_confirmar"},
            )
