from __future__ import annotations

from . import state_historico


class MainWindowHandlersHistoricoMixin:
    def _apply_historico_default_range(self) -> None:
        aplicar_ultimo_rango = getattr(self, "_apply_historico_last_30_days", None)
        if callable(aplicar_ultimo_rango):
            aplicar_ultimo_rango()
            return
        state_historico.aplicar_rango_por_defecto_historico(self)
