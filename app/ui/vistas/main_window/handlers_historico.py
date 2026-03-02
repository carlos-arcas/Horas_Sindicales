from __future__ import annotations

import logging
from typing import Any

from app.ui.vistas import historico_actions
from app.ui.vistas.main_window import state_historico


logger = logging.getLogger(__name__)


class HandlersHistorico:
    def __init__(self, window: Any) -> None:
        self._window = window

    def apply_historico_default_range(self) -> None:
        aplicar_ultimo_rango = getattr(self._window, "_apply_historico_last_30_days", None)
        if callable(aplicar_ultimo_rango):
            aplicar_ultimo_rango()
            return
        state_historico.aplicar_rango_por_defecto_historico(self._window)

    def on_historico_periodo_mode_changed(self, _checked: bool | None = None) -> None:
        required = (
            "historico_periodo_anual_radio",
            "historico_periodo_mes_radio",
            "historico_periodo_rango_radio",
        )
        for widget_name in required:
            if getattr(self._window, widget_name, None) is None:
                logger.warning(
                    "ui_handler_widget_missing",
                    extra={"handler": "on_historico_periodo_mode_changed", "widget": widget_name},
                )
                return
        historico_actions.on_historico_periodo_mode_changed(self._window)
