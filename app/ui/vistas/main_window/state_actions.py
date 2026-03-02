from __future__ import annotations

from . import data_refresh, state_historico


class MainWindowStateActionsMixin:
    """Acciones reutilizables para gestionar estado y refresco de la UI."""

    def _set_processing_state(self, in_progress: bool) -> None:
        from .state_helpers import set_processing_state

        set_processing_state(self, in_progress)

    def _apply_historico_filters(self) -> None:
        state_historico.aplicar_filtros_historico(self)

    def _cargar_datos_iniciales(self) -> None:
        self._load_personas()
        self._reload_pending_views()
        data_refresh.refresh_saldos(self)

    def _update_global_context(self) -> None:
        refresh_header = getattr(self, "_refresh_header_title", None)
        if callable(refresh_header):
            refresh_header()

        update_actions = getattr(self, "_update_action_state", None)
        if callable(update_actions):
            update_actions()
