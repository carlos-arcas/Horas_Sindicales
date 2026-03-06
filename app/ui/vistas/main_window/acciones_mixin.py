from __future__ import annotations

import logging

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text
from app.ui.vistas.main_window.importaciones import (
    MainWindowHealthMixin,
    acciones_pendientes,
    acciones_sincronizacion,
    ask_push_after_pdf,
    execute_confirmar_with_pdf,
    finalize_confirmar_with_pdf,
    historico_actions,
    on_confirmar as on_confirmar_handler,
    on_insertar_sin_pdf,
    show_confirmation_closure,
    show_pdf_actions_dialog,
    toast_error,
    undo_confirmation,
)
from . import validacion_preventiva

logger = logging.getLogger(__name__)


class AccionesMainWindowMixin:
    def _execute_confirmar_with_pdf(self, persona, selected, pdf_path: str):
        return execute_confirmar_with_pdf(self, persona, selected, pdf_path)

    def _finalize_confirmar_with_pdf(
        self,
        persona,
        correlation_id,
        generado,
        creadas,
        confirmadas_ids,
        errores,
        pendientes_restantes,
    ) -> None:
        return finalize_confirmar_with_pdf(
            self,
            persona,
            correlation_id,
            generado,
            creadas,
            confirmadas_ids,
            errores,
            pendientes_restantes,
        )

    def _show_confirmation_closure(self, creadas, errores, *, operation_name: str, correlation_id: str | None = None) -> None:
        return show_confirmation_closure(
            self,
            creadas,
            errores,
            operation_name=operation_name,
            correlation_id=correlation_id,
        )

    def _show_pdf_actions_dialog(self, generated_path) -> None:
        return show_pdf_actions_dialog(self, generated_path)

    def _ask_push_after_pdf(self) -> None:
        return ask_push_after_pdf(self)

    def _undo_confirmation(self, solicitud_ids: list[int]) -> None:
        return undo_confirmation(self, solicitud_ids)

    def _procesar_resultado_confirmacion(
        self,
        confirmadas_ids: list[int],
        errores: list[str],
        pendientes_restantes,
    ) -> None:
        self._solicitudes_controller.aplicar_confirmacion(confirmadas_ids, pendientes_restantes)
        self._reload_pending_views()
        self._refresh_historico()
        self._refresh_saldos()
        if errores:
            self.toast.warning("\n".join(errores), title=copy_text("ui.validacion.validacion"))

    def _on_open_saldos_modal(self) -> None:
        from . import acciones_personas

        return acciones_personas.on_open_saldos_modal(self)

    def _on_completo_changed(self, checked: object = False, *_args: object, **_kwargs: object) -> None:
        from . import form_handlers

        return form_handlers.on_completo_changed(self, checked)

    def _on_add_pendiente(self, *args, **kwargs) -> None:
        from . import acciones_pendientes as acciones

        return acciones.on_add_pendiente(self, *args, **kwargs)

    def _on_open_historico_detalle(self) -> None:
        return historico_actions.on_open_historico_detalle(self)

    def _on_generar_pdf_historico(self) -> None:
        return historico_actions.on_generar_pdf_historico(self)

    def _on_export_historico_pdf(self) -> None:
        return historico_actions.on_export_historico_pdf(self)

    def _on_eliminar(self) -> None:
        return historico_actions.on_eliminar(self)

    def _bind_preventive_validation_events(self) -> None:
        return validacion_preventiva._bind_preventive_validation_events(self)

    def _mark_field_touched(self, field: str) -> None:
        return validacion_preventiva._mark_field_touched(self, field)

    def _schedule_preventive_validation(self) -> None:
        return validacion_preventiva._schedule_preventive_validation(self)

    def _run_preventive_validation(self) -> None:
        return validacion_preventiva._run_preventive_validation(self)

    def _collect_base_preventive_errors(self) -> dict[str, str]:
        return validacion_preventiva._collect_base_preventive_errors(self)

    def _collect_preventive_validation(self) -> tuple[dict[str, str], dict[str, str]]:
        return validacion_preventiva._collect_preventive_validation(self)

    def _build_preview_solicitud(self):
        from . import form_handlers

        return form_handlers.build_preview_solicitud(self)

    def _collect_preventive_business_rules(
        self, errors: dict[str, str], warnings: dict[str, str]
    ) -> None:
        return validacion_preventiva._collect_preventive_business_rules(
            self, errors, warnings
        )

    def _collect_pending_duplicates_warning(self, warnings: dict[str, str]) -> None:
        return validacion_preventiva._collect_pending_duplicates_warning(self, warnings)

    def _on_go_to_existing_duplicate(self) -> None:
        return validacion_preventiva._on_go_to_existing_duplicate(self)

    def _on_pending_selection_changed(self, *args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        self._refrescar_estado_operativa("pendiente_selected")

    def _prompt_confirm_pdf_path(self, selected: object) -> str | None:
        from pathlib import Path

        from app.ui.qt_compat import QFileDialog
        from app.ui.vistas.confirmacion_adaptador_qt import resolver_colision_destino_pdf

        if not isinstance(selected, list) or not selected:
            return None

        sugerir_nombre = getattr(self._solicitud_use_cases, "sugerir_nombre_pdf", None)
        if not callable(sugerir_nombre):
            return None

        default_name = sugerir_nombre(selected)
        output_dir = getattr(self, "_output_dir", None)
        default_dir = Path(output_dir) if output_dir else Path.cwd()
        default_path = str(default_dir / default_name)
        pdf_path, _ = QFileDialog.getSaveFileName(
            self,
            copy_text("ui.confirmacion.guardar_pdf"),
            default_path,
            copy_text("ui.confirmacion.filtro_pdf"),
        )
        if not pdf_path:
            return None
        return resolver_colision_destino_pdf(self, pdf_path)

    def _on_toggle_ver_todas_pendientes(self, checked: bool) -> None:
        self._pending_view_all = checked
        self._refresh_pending_ui_state()

    def _on_remove_pendiente(self) -> None:
        return acciones_pendientes.on_remove_pendiente(self)

    def _on_insertar_sin_pdf(self) -> None:
        return on_insertar_sin_pdf(self)

    def _on_confirmar(self, *args, **kwargs) -> None:
        _ = (args, kwargs)
        try:
            persona_actual = self._current_persona()
            if persona_actual is None:
                self.toast.warning(
                    copy_text("ui.sync.delegada_no_seleccionada"),
                    title=copy_text("ui.validacion.validacion"),
                )
                return
            confirmar_action = on_confirmar_handler
            if not callable(confirmar_action):
                mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
                detalle = copy_text("ui.errores.reintenta_contacta_soporte")
                toast_error(self.toast, f"{mensaje}. {detalle}")
                log_operational_error(
                    logger,
                    "UI_CONFIRMAR_HANDLER_NO_DISPONIBLE",
                    extra={
                        "handler": "on_confirmar",
                        "contexto": "mainwindow._on_confirmar",
                    },
                )
                return
            confirmar_action(self)
        except Exception as exc:
            mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
            detalle = copy_text("ui.errores.reintenta_contacta_soporte")
            toast_error(self.toast, f"{mensaje}. {detalle}")
            log_operational_error(
                logger,
                "UI_CONFIRMAR_HANDLER_FALLO",
                exc=exc,
                extra={
                    "handler": "on_confirmar",
                    "contexto": "mainwindow._on_confirmar",
                },
            )

    def _render_preventive_validation(self) -> None:
        return validacion_preventiva._render_preventive_validation(self)

    def _run_preconfirm_checks(self) -> bool:
        return validacion_preventiva._run_preconfirm_checks(self)

    def _on_sync(self) -> None:
        return acciones_sincronizacion.on_sync(self)

    def _on_simulate_sync(self) -> None:
        return acciones_sincronizacion.on_simulate_sync(self)

    def _on_confirm_sync(self) -> None:
        return acciones_sincronizacion.on_confirm_sync(self)

    def _on_retry_failed(self) -> None:
        return acciones_sincronizacion.on_retry_failed(self)

    def _on_show_sync_details(self) -> None:
        return acciones_sincronizacion.on_show_sync_details(self)

    def _on_copy_sync_report(self) -> None:
        return acciones_sincronizacion.on_copy_sync_report(self)

    def _on_open_sync_logs(self) -> None:
        return acciones_sincronizacion.on_open_sync_logs(self)

    def _on_show_sync_history(self) -> None:
        return acciones_sincronizacion.on_show_sync_history(self)

    def _on_review_conflicts(self) -> None:
        return acciones_sincronizacion.on_review_conflicts(self)

    def _on_open_opciones(self) -> None:
        return acciones_sincronizacion.on_open_opciones(self)

    def _on_edit_grupo(self) -> None:
        return self._on_open_opciones()

    def _on_edit_pdf(self) -> None:
        return self._on_open_opciones()

    def _on_snooze_alerts_today(self) -> None:
        return MainWindowHealthMixin._on_snooze_alerts_today(self)

    def _on_sync_finished(self, summary) -> None:
        return acciones_sincronizacion.on_sync_finished(self, summary)

    def _on_sync_failed(self, payload: object) -> None:
        return acciones_sincronizacion.on_sync_failed(self, payload)

    def _show_sync_details_dialog(self) -> None:
        return acciones_sincronizacion.show_sync_details_dialog(self)

    def _apply_sync_report(self, report) -> None:
        return acciones_sincronizacion.apply_sync_report(self, report)

    def _clear_pendientes(self) -> None:
        return acciones_pendientes.on_clear_pendientes(self)

    def _on_review_hidden_pendientes(self) -> None:
        return acciones_pendientes.on_review_hidden(self)

    def _on_remove_huerfana(self) -> None:
        return acciones_pendientes.on_remove_huerfana(self)
