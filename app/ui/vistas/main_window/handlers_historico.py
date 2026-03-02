from __future__ import annotations

import logging
from typing import Any

from . import state_historico

logger = logging.getLogger(__name__)


class HandlersHistorico:
    def __init__(self, window: Any) -> None:
        self._window = window

    def apply_historico_default_range(self) -> None:
        window = self._window
        aplicar_ultimo_rango = getattr(window, "_apply_historico_last_30_days", None)
        if callable(aplicar_ultimo_rango):
            aplicar_ultimo_rango()
            return
        state_historico.aplicar_rango_por_defecto_historico(window)

    def on_historico_periodo_mode_changed(self, _checked: bool | None = None) -> None:
        window = self._window
        widgets = (
            "historico_periodo_anual_radio",
            "historico_periodo_mes_radio",
            "historico_periodo_rango_radio",
            "historico_periodo_anual_spin",
            "historico_periodo_mes_ano_spin",
            "historico_periodo_mes_combo",
            "historico_desde_date",
            "historico_hasta_date",
        )
        faltantes = [name for name in widgets if getattr(window, name, None) is None]
        if faltantes:
            logger.warning(
                "ui_historico_widgets_faltantes",
                extra={"handler": "_on_historico_periodo_mode_changed", "widgets": faltantes},
            )
            return
        anual_activo = window.historico_periodo_anual_radio.isChecked()
        mes_activo = window.historico_periodo_mes_radio.isChecked()
        rango_activo = window.historico_periodo_rango_radio.isChecked()

        window.historico_periodo_anual_spin.setEnabled(anual_activo)
        window.historico_periodo_mes_ano_spin.setEnabled(mes_activo)
        window.historico_periodo_mes_combo.setEnabled(mes_activo)
        window.historico_desde_date.setEnabled(rango_activo)
        window.historico_hasta_date.setEnabled(rango_activo)
