from __future__ import annotations

import logging

from app.application.dto import SolicitudDTO

from . import (
    data_refresh,
    form_handlers,
    state_historico,
    state_pendientes,
    validacion_preventiva,
)

try:
    from .state_helpers import update_action_state
except Exception:  # pragma: no cover

    def update_action_state(_window) -> None:
        return


from app.ui.vistas.main_window.importaciones import (
    acciones_pendientes,
    build_estado_pendientes_debug_payload,
    historico_actions,
    log_estado_pendientes,
)

logger = logging.getLogger(__name__)


class RefrescoMainWindowMixin:
    def _refrescar_estado_operativa(self, motivo: str) -> None:
        logger.debug("UI_RESERVED_BALANCE_REFRESH", extra={"motivo": motivo})
        self._update_solicitud_preview()
        self._update_pending_totals()
        self._refresh_saldos()
        self._update_action_state()

    def _refresh_historico(self, *, force: bool = False) -> None:
        data_refresh.refresh_historico(self, force=force)

    def _refresh_saldos(self) -> None:
        data_refresh.refresh_saldos(self)

    def _reload_pending_views(self) -> None:
        data_refresh.reload_pending_views(self)

    def _update_action_state(self) -> None:
        update_action_state(self)

    def _update_solicitud_preview(self, *_args: object) -> None:
        return validacion_preventiva._update_solicitud_preview(self)

    def _apply_historico_text_filter(self) -> None:
        return state_historico.aplicar_filtro_texto_historico(self)

    def _apply_historico_default_range(self) -> None:
        aplicar_ultimo_rango = getattr(self, "_apply_historico_last_30_days", None)
        if callable(aplicar_ultimo_rango):
            aplicar_ultimo_rango()
            return
        state_historico.aplicar_rango_por_defecto_historico(self)

    def _historico_period_filter_state(self) -> tuple[str, int | None, int | None]:
        return state_historico.estado_filtro_periodo_historico(self)

    def _update_historico_empty_state(self) -> None:
        return state_historico.actualizar_estado_vacio_historico(self)

    def _on_historico_escape(self) -> None:
        return state_historico.manejar_escape_historico(self)

    def _selected_historico_solicitudes(self) -> list[SolicitudDTO]:
        return state_historico.obtener_solicitudes_historico_seleccionadas(self)

    def _selected_historico(self) -> SolicitudDTO | None:
        return state_historico.obtener_solicitud_historico_seleccionada(self)

    def _on_historico_select_all_visible_toggled(self, checked: bool) -> None:
        return state_historico.alternar_seleccion_visible_historico(self, checked)

    def _on_historico_selection_changed(self, *_args: object) -> None:
        state_historico.actualizar_estado_seleccion_historico(self)
        self._update_action_state()

    def _sync_historico_select_all_visible_state(self) -> None:
        return state_historico.sincronizar_estado_seleccion_visible_historico(self)

    def _notify_historico_filter_if_hidden(
        self, solicitudes_insertadas: list[SolicitudDTO]
    ) -> None:
        return historico_actions.notify_historico_filter_if_hidden(
            self, solicitudes_insertadas
        )

    def _selected_pending_row_indexes(self) -> list[int]:
        return state_pendientes.obtener_indices_filas_pendientes_seleccionadas(self)

    def _selected_pending_solicitudes(self) -> list[SolicitudDTO]:
        selected_rows = self._selected_pending_row_indexes()
        return [
            self._pending_solicitudes[row]
            for row in selected_rows
            if 0 <= row < len(self._pending_solicitudes)
        ]

    def _obtener_ids_seleccionados_pendientes(self) -> list[int]:
        return sorted(
            {
                solicitud.id
                for solicitud in self._selected_pending_solicitudes()
                if solicitud is not None and solicitud.id is not None
            }
        )

    def _selected_pending_for_editing(self) -> SolicitudDTO | None:
        return state_pendientes.obtener_pendiente_para_edicion(self)

    def _find_pending_row_by_id(self, solicitud_id: int | None) -> int | None:
        return state_pendientes.buscar_fila_pendiente_por_id(self, solicitud_id)

    def _focus_pending_row(self, row: int) -> None:
        return state_pendientes.enfocar_fila_pendiente(self, row)

    def _focus_pending_by_id(self, solicitud_id: int | None) -> bool:
        return state_pendientes.enfocar_pendiente_por_id(self, solicitud_id)

    def _dump_estado_pendientes(self, motivo: str) -> None:
        try:
            estado = build_estado_pendientes_debug_payload(
                editing_pending=self._selected_pending_for_editing(),
                selected_rows=self._selected_pending_row_indexes(),
                solicitud_form=form_handlers.build_preview_solicitud(self),
                pending_solicitudes=self._pending_solicitudes,
                agregar_button_text=self.agregar_button.text(),
                agregar_button_enabled=self.agregar_button.isEnabled(),
            )
            log_estado_pendientes(motivo, estado)
        except Exception:
            logger.exception("estado_pendientes_dump_failed", extra={"motivo": motivo})

    def _update_pending_totals(self) -> None:
        return acciones_pendientes.helper_update_pending_totals(self)

    def _refresh_pending_conflicts(self) -> None:
        return acciones_pendientes.helper_refresh_pending_conflicts(self)

    def _refresh_pending_ui_state(self) -> None:
        return acciones_pendientes.helper_refresh_pending_ui_state(self)
