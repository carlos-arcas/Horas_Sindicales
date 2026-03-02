from __future__ import annotations

from datetime import date

from app.application.dto import PeriodoFiltro
from app.ui.copy_catalog import copy_text

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

    def _apply_help_preferences(self) -> None:
        show_help_toggle = getattr(self, "show_help_toggle", None)
        if show_help_toggle is None:
            return

        settings_key = copy_text("ui.preferencias.settings_show_help_key")
        raw_value = self._settings.value(settings_key, True)
        show_help = raw_value.strip().lower() in {"1", "true", "yes", "on"} if isinstance(raw_value, str) else bool(raw_value)
        show_help_toggle.blockSignals(True)
        show_help_toggle.setChecked(show_help)
        show_help_toggle.blockSignals(False)
        if getattr(self, "_help_toggle_conectado", False):
            show_help_toggle.toggled.disconnect(self._on_help_toggle_changed)
            self._help_toggle_conectado = False
        show_help_toggle.toggled.connect(self._on_help_toggle_changed)
        self._help_toggle_conectado = True
        self._on_help_toggle_changed(show_help)

    def _current_saldo_filtro(self) -> PeriodoFiltro:
        fecha_input = getattr(self, "fecha_input", None)
        if fecha_input is not None and hasattr(fecha_input, "date"):
            fecha = fecha_input.date()
            if hasattr(fecha, "isValid") and fecha.isValid():
                return PeriodoFiltro.mensual(fecha.year(), fecha.month())
        return PeriodoFiltro.anual(date.today().year)

    def _update_periodo_label(self) -> None:
        saldos_card = getattr(self, "saldos_card", None)
        if saldos_card is None or not hasattr(saldos_card, "update_periodo_label"):
            return

        filtro = self._current_saldo_filtro()
        if filtro.modo == "MENSUAL" and filtro.month is not None:
            saldos_card.update_periodo_label(f"Mensual ({filtro.month:02d}/{filtro.year})")
            return
        saldos_card.update_periodo_label(f"Anual ({filtro.year})")

    def _set_saldos_labels(self, resumen) -> None:
        saldos_card = getattr(self, "saldos_card", None)
        if saldos_card is None or not hasattr(saldos_card, "update_saldos"):
            return
        saldos_card.update_saldos(resumen)
