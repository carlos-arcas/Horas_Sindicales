from __future__ import annotations

from app.ui.vistas.main_window.ajustes_post_build import (
    actualizar_columnas_responsivas,
    configurar_placeholders_hora,
    normalizar_alturas_inputs,
)


class AjustesPostBuildMixin:
    def _configure_time_placeholders(self) -> None:
        i18n = getattr(self, "_i18n", None) or getattr(self, "i18n", None)
        configurar_placeholders_hora(self, i18n)

    def _update_responsive_columns(self) -> None:
        actualizar_columnas_responsivas(self)

    def _normalize_input_heights(self) -> None:
        normalizar_alturas_inputs(self)
