from __future__ import annotations

import logging

try:
    from PySide6.QtCore import QDate
    from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QVBoxLayout
except Exception:  # pragma: no cover
    QDate = QDialog = QHBoxLayout = QPushButton = QVBoxLayout = object

from app.application.dto import PeriodoFiltro, SolicitudDTO
from app.core.observability import OperationContext
from app.ui.copy_catalog import copy_text
from app.ui.group_dialog import GrupoConfigDialog, PdfConfigDialog
from app.ui.toast_helpers import toast_success
from app.ui.vistas.main_window_helpers import build_estado_pendientes_debug_payload, log_estado_pendientes
from app.ui.vistas import historico_actions

logger = logging.getLogger(__name__)


class MainWindowStateActionsMixin:
    def _update_global_context(self) -> None:
        return

    def _apply_help_preferences(self) -> None:
        saved = self._settings.value("ux/mostrar_ayuda", True, type=bool)
        if self.show_help_toggle is not None:
            self.show_help_toggle.setChecked(bool(saved))
            self.show_help_toggle.toggled.connect(self._on_toggle_help)
        self._set_help_visibility(bool(saved))

    def _on_toggle_help(self, checked: bool) -> None:
        self._settings.setValue("ux/mostrar_ayuda", checked)
        self._set_help_visibility(bool(checked))

    def _set_help_visibility(self, visible: bool) -> None:
        for tip in (self.solicitudes_tip_1, self.solicitudes_tip_2, self.solicitudes_tip_3):
            if tip is not None:
                tip.setVisible(visible)
        self._apply_solicitudes_tooltips()

    def _apply_solicitudes_tooltips(self) -> None:
        if self.persona_combo is None:
            return
        extended = bool(self.show_help_toggle is None or self.show_help_toggle.isChecked())
        self.persona_combo.setToolTip(copy_text("solicitudes.tooltip_delegada") if extended else "")
        self.fecha_input.setToolTip(copy_text("solicitudes.tooltip_fecha") if extended else "")
        self.desde_input.setToolTip(copy_text("solicitudes.tooltip_desde") if extended else "")
        self.hasta_input.setToolTip(copy_text("solicitudes.tooltip_hasta") if extended else "")
        self.total_preview_input.setToolTip(copy_text("solicitudes.tooltip_minutos") if extended else "")
        self.notas_input.setToolTip(copy_text("solicitudes.tooltip_notas") if extended else "")

    def _on_open_saldos_modal(self) -> None:
        logger.info("UI_SALDOS_MODAL_OPEN")
        dialog = QDialog(self)
        dialog.setWindowTitle("Saldos detallados")
        dialog.resize(800, 500)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        saldos_widget = self.saldos_card.__class__(dialog)
        saldos_widget.update_periodo_label(self.saldos_card.saldo_periodo_label.text())
        saldos_widget.saldo_periodo_consumidas.setText(self.saldos_card.saldo_periodo_consumidas.text())
        saldos_widget.saldo_periodo_restantes.setText(self.saldos_card.saldo_periodo_restantes.text())
        saldos_widget.saldo_anual_consumidas.setText(self.saldos_card.saldo_anual_consumidas.text())
        saldos_widget.saldo_anual_restantes.setText(self.saldos_card.saldo_anual_restantes.text())
        saldos_widget.saldo_grupo_consumidas.setText(self.saldos_card.saldo_grupo_consumidas.text())
        saldos_widget.saldo_grupo_restantes.setText(self.saldos_card.saldo_grupo_restantes.text())
        saldos_widget.bolsa_mensual_label.setText(self.saldos_card.bolsa_mensual_label.text())
        saldos_widget.bolsa_delegada_label.setText(self.saldos_card.bolsa_delegada_label.text())
        saldos_widget.bolsa_grupo_label.setText(self.saldos_card.bolsa_grupo_label.text())
        saldos_widget.exceso_badge.setText(self.saldos_card.exceso_badge.text())
        saldos_widget.exceso_badge.setVisible(self.saldos_card.exceso_badge.isVisible())
        saldos_widget.saldos_details_button.setChecked(True)
        layout.addWidget(saldos_widget, 1)
        close_button = QPushButton("Cerrar")
        close_button.setProperty("variant", "secondary")
        close_button.clicked.connect(dialog.accept)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)
        dialog.exec()

    def _on_completo_changed(self, checked: bool) -> None:
        self._sync_completo_visibility(checked)
        self._update_solicitud_preview()

    def _on_fecha_changed(self) -> None:
        if self.completo_check.isChecked():
            self.completo_check.setChecked(False)
        self._update_solicitud_preview()

    def _configure_time_placeholders(self) -> None:
        self.desde_placeholder.setVisible(False)
        self.hasta_placeholder.setVisible(False)
        self.desde_placeholder.setFixedSize(self.desde_container.sizeHint())
        self.hasta_placeholder.setFixedSize(self.hasta_container.sizeHint())
        self._sync_completo_visibility(self.completo_check.isChecked())
        self._bind_manual_hours_preview_refresh()

    def _sync_completo_visibility(self, checked: bool) -> None:
        self.desde_input.setEnabled(not checked)
        self.hasta_input.setEnabled(not checked)
        self.desde_container.setToolTip(copy_text("solicitudes.no_aplica_completo") if checked else "")
        self.hasta_container.setToolTip(copy_text("solicitudes.no_aplica_completo") if checked else "")

    def _on_edit_grupo(self) -> None:
        dialog = GrupoConfigDialog(self._grupo_use_cases, self._sync_service, self)
        if dialog.exec():
            self._refresh_saldos()

    def _on_edit_pdf(self) -> None:
        PdfConfigDialog(self._grupo_use_cases, self._sync_service, self).exec()

    def _focus_historico_search(self) -> None:
        self.main_tabs.setCurrentIndex(1)
        historico_actions.focus_historico_search(self)

    def _on_historico_todas_delegadas_toggled(self, checked: bool) -> None:
        self.historico_delegada_combo.setEnabled(not checked)
        if checked:
            self.historico_delegada_combo.setCurrentIndex(0)

    def _update_action_state(self) -> None:
        from .state_helpers import update_action_state
        update_action_state(self)

    def _build_debug_estado_pendientes(self) -> dict[str, object]:
        return build_estado_pendientes_debug_payload(
            editing_pending=self._selected_pending_for_editing(),
            selected_rows=self._selected_pending_row_indexes(),
            solicitud_form=self._build_preview_solicitud(),
            pending_solicitudes=self._pending_solicitudes,
            agregar_button_text=self.agregar_button.text(),
            agregar_button_enabled=bool(self.agregar_button.isEnabled()),
        )

    def _dump_estado_pendientes(self, motivo: str) -> dict:
        try:
            estado = self._build_debug_estado_pendientes()
        except Exception as exc:
            estado = {"motivo": motivo, "error": str(exc)}
            logger.exception("estado_pendientes_failed motivo=%s", motivo)
            return estado
        log_estado_pendientes(motivo, estado)
        return estado

    def _on_pending_selection_changed(self) -> None:
        self._dump_estado_pendientes("selection_changed_pending")
        self._update_action_state()

    def _undo_last_added_pending(self, solicitud_id: int | None) -> None:
        if solicitud_id is None:
            return
        try:
            with OperationContext("deshacer_pendiente") as operation:
                self._solicitud_use_cases.eliminar_solicitud(solicitud_id, correlation_id=operation.correlation_id)
        except Exception as exc:
            logger.exception("Error al deshacer pendiente")
            self._show_critical_error(exc)
            return
        self._reload_pending_views()
        self._refresh_saldos()
        self.toast.info("Pendiente deshecha")

    def _reconstruir_tabla_pendientes(self) -> None:
        self._refresh_pending_ui_state()
        if self._pending_solicitudes:
            return
        self._duplicate_target = None
        self._blocking_errors.pop("duplicado", None)
        self.goto_existing_button.setVisible(False)
        self._render_preventive_validation()

    def _post_confirm_success(self, confirmadas_ids: list[int], pendientes_restantes: list[SolicitudDTO] | None = None) -> None:
        if not confirmadas_ids:
            logger.warning("UI_POST_CONFIRM_NO_IDS")
        self._solicitudes_controller.aplicar_confirmacion(confirmadas_ids, pendientes_restantes)
        self._reconstruir_tabla_pendientes()
        self._refrescar_historico()
        self._clear_form()
        self.pendientes_table.clearSelection()
        self._editing_solicitud_id = None
        self._update_global_context()

    def _procesar_resultado_confirmacion(self, confirmadas_ids: list[int], errores: list[str], pendientes_restantes: list[SolicitudDTO] | None = None) -> None:
        if confirmadas_ids:
            self._post_confirm_success(confirmadas_ids, pendientes_restantes)
            self._refresh_saldos()
            toast_success(self.toast, f"{len(confirmadas_ids)} solicitudes confirmadas", title="Confirmación")
            if errores:
                self.toast.warning(f"{len(errores)} errores", title="Confirmación")
        elif errores:
            self.toast.warning("No se pudo confirmar ninguna solicitud", title="Confirmación")

    def _on_add_pendiente(self) -> None:
        logger.info("CLICK add_or_update_pendiente handler=_on_add_pendiente")
        self._dump_estado_pendientes("click_add_or_update_pending")
        if not self._ui_ready:
            logger.info("_on_add_pendiente early_return motivo=ui_not_ready")
            return
        self._field_touched.update({"delegada", "fecha", "tramo"})
        self._run_preventive_validation()
        if self._blocking_errors:
            logger.info("_on_add_pendiente early_return motivo=blocking_errors")
            self.toast.warning("Corrige los errores pendientes antes de añadir.", title="Validación preventiva")
            return
        self._solicitudes_controller.on_add_pendiente()

    def _update_periodo_label(self) -> None:
        self.saldos_card.update_periodo_label("Mensual")

    def _set_saldos_labels(self, resumen, pendientes_periodo: int = 0, pendientes_ano: int = 0) -> None:
        self.saldos_card.update_saldos(resumen, pendientes_periodo, pendientes_ano)

    def _on_historico_selection_changed(self) -> None:
        self._update_action_state()

    def _current_saldo_filtro(self) -> PeriodoFiltro:
        periodo_base = self.fecha_input.date() if hasattr(self, "fecha_input") else QDate.currentDate()
        return PeriodoFiltro.mensual(periodo_base.year(), periodo_base.month())

    def _on_toggle_ver_todas_pendientes(self, checked: bool) -> None:
        self._pending_view_all = checked
        self.persona_combo.setEnabled(not checked)
        self._reload_pending_views()

    def _refrescar_historico(self) -> None:
        self._refresh_historico()
