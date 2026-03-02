from __future__ import annotations

import logging

from app.ui.copy_catalog import copy_text

from . import dialogos_sincronizacion
from .ui_layout_helpers import normalize_input_heights as _normalize_input_heights
from .ui_layout_helpers import update_responsive_columns as _update_responsive_columns

logger = logging.getLogger(__name__)


class HandlersLayout:
    def __init__(self, window: object) -> None:
        self._window = window

    def configure_time_placeholders(self) -> None:
        configure_time_placeholders(self._window)

    def configure_operativa_focus_order(self) -> None:
        configure_operativa_focus_order(self._window)

    def normalize_input_heights(self) -> None:
        normalize_input_heights(self._window)

    def update_responsive_columns(self) -> None:
        update_responsive_columns(self._window)

    def status_to_label(self, status: str) -> str:
        return status_to_label(status)


def configure_time_placeholders(window: object) -> None:
    """Configura formato y ayuda de hora sin asumir disponibilidad de widgets."""
    for input_name in ("desde_input", "hasta_input"):
        input_widget = getattr(window, input_name, None)
        if input_widget is None:
            logger.warning("UI_WIDGET_MISSING_FOR_TIME_PLACEHOLDER", extra={"widget": input_name})
            continue
        if hasattr(input_widget, "setDisplayFormat"):
            input_widget.setDisplayFormat(copy_text("ui.solicitudes.formato_hora"))
        if hasattr(input_widget, "setToolTip"):
            input_widget.setToolTip(copy_text("ui.solicitudes.tooltip_formato_hora"))


def configure_operativa_focus_order(window: object) -> None:
    focus_chain = (
        ("persona_combo", "fecha_input"),
        ("fecha_input", "desde_input"),
        ("desde_input", "hasta_input"),
        ("hasta_input", "completo_check"),
        ("completo_check", "notas_input"),
        ("notas_input", "agregar_button"),
        ("agregar_button", "insertar_sin_pdf_button"),
        ("insertar_sin_pdf_button", "confirmar_button"),
    )
    set_tab_order = getattr(window, "setTabOrder", None)
    if not callable(set_tab_order):
        logger.warning("UI_SET_TAB_ORDER_NOT_AVAILABLE")
        return

    for before_name, after_name in focus_chain:
        before_widget = getattr(window, before_name, None)
        after_widget = getattr(window, after_name, None)
        if before_widget is None or after_widget is None:
            logger.warning(
                "UI_TAB_ORDER_SKIPPED_MISSING_WIDGET",
                extra={"before": before_name, "after": after_name},
            )
            continue
        set_tab_order(before_widget, after_widget)


def normalize_input_heights(window: object) -> None:
    _normalize_input_heights(window)


def update_responsive_columns(window: object) -> None:
    _update_responsive_columns(window)


def status_to_label(status: str) -> str:
    try:
        return dialogos_sincronizacion.status_to_label(status)
    except Exception:
        return status
