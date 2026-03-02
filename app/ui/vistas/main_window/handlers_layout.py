from __future__ import annotations

import logging

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text

from .ui_layout_helpers import normalize_input_heights, update_responsive_columns

logger = logging.getLogger(__name__)


class MainWindowHandlersLayoutMixin:
    def _normalize_input_heights(self) -> None:
        try:
            normalize_input_heights(self)
        except Exception as exc:
            log_operational_error(
                logger,
                "UI_NORMALIZE_INPUT_HEIGHTS_FAILED",
                exc=exc,
                extra={"contexto": "MainWindow._normalize_input_heights"},
            )

    def _update_responsive_columns(self) -> None:
        try:
            update_responsive_columns(self)
        except Exception as exc:
            log_operational_error(
                logger,
                "UI_UPDATE_RESPONSIVE_COLUMNS_FAILED",
                exc=exc,
                extra={"contexto": "MainWindow._update_responsive_columns"},
            )

    def _configure_time_placeholders(self) -> None:
        formato_hora = copy_text("ui.solicitudes.formato_hora")
        for widget_name in ("desde_input", "hasta_input"):
            widget = getattr(self, widget_name, None)
            if widget is not None and hasattr(widget, "setDisplayFormat"):
                widget.setDisplayFormat(formato_hora)

        is_completo = bool(getattr(self.completo_check, "isChecked", lambda: False)())
        for container_name, placeholder_name in (
            ("desde_container", "desde_placeholder"),
            ("hasta_container", "hasta_placeholder"),
        ):
            container = getattr(self, container_name, None)
            placeholder = getattr(self, placeholder_name, None)
            if container is None or placeholder is None:
                continue
            placeholder.setFixedWidth(container.sizeHint().width())
            placeholder.setVisible(is_completo)
            container.setVisible(not is_completo)
