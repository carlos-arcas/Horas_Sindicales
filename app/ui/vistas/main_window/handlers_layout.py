from __future__ import annotations

import logging
from typing import Any

from app.bootstrap.logging import log_operational_error
from app.ui.vistas.main_window import acciones_personas, dialogos_sincronizacion
from app.ui.vistas.main_window.ui_layout_helpers import normalize_input_heights, update_responsive_columns


logger = logging.getLogger(__name__)


class HandlersLayout:
    def __init__(self, window: Any) -> None:
        self._window = window

    def normalize_input_heights(self) -> None:
        try:
            normalize_input_heights(self._window)
        except Exception as exc:
            log_operational_error(
                logger,
                "UI_NORMALIZE_INPUT_HEIGHTS_FAILED",
                exc=exc,
                extra={"contexto": "mainwindow._normalize_input_heights"},
            )

    def update_responsive_columns(self) -> None:
        try:
            update_responsive_columns(self._window)
        except Exception as exc:
            log_operational_error(
                logger,
                "UI_UPDATE_RESPONSIVE_COLUMNS_FAILED",
                exc=exc,
                extra={"contexto": "mainwindow._update_responsive_columns"},
            )

    def status_to_label(self, status: str) -> str:
        try:
            return dialogos_sincronizacion.status_to_label(status)
        except Exception:
            return status

    def configure_operativa_focus_order(self) -> None:
        required = ("persona_combo", "fecha_input", "desde_input", "hasta_input")
        for widget_name in required:
            if getattr(self._window, widget_name, None) is None:
                logger.warning(
                    "ui_handler_widget_missing",
                    extra={"handler": "configure_operativa_focus_order", "widget": widget_name},
                )
                return
        acciones_personas.configure_operativa_focus_order(self._window)
