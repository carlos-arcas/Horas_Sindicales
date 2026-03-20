from __future__ import annotations

import logging

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text
from app.ui.toast_helpers import toast_error
from app.ui.vistas import historico_actions
from app.ui.vistas.confirmacion_actions import (
    ask_push_after_pdf,
    execute_confirmar_with_pdf,
    finalize_confirmar_with_pdf,
    on_confirmar as on_confirmar_handler,
    on_insertar_sin_pdf,
    show_confirmation_closure,
    show_pdf_actions_dialog,
    undo_confirmation,
)
from app.ui.vistas.main_window_health_mixin import MainWindowHealthMixin

from . import acciones_pendientes, acciones_sincronizacion
from . import validacion_preventiva

logger = logging.getLogger(__name__)


HANDLERS_UI_CRITICOS = (
    "_apply_historico_default_range",
    "_apply_historico_filters",
    "_bind_preventive_validation_events",
    "_configure_historico_focus_order",
    "_configure_operativa_focus_order",
    "_configure_time_placeholders",
    "_current_persona",
    "_focus_historico_search",
    "_normalize_input_heights",
    "_on_historico_escape",
    "_on_historico_filter_changed",
    "_on_historico_periodo_mode_changed",
    "_on_open_historico_detalle",
    "_on_open_saldos_modal",
    "_refresh_historico",
    "_refresh_saldos",
    "_restaurar_contexto_guardado",
    "_restore_draft_for_persona",
    "_status_to_label",
    "_update_action_state",
    "_update_responsive_columns",
    "_update_solicitud_preview",
)


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

    def _show_confirmation_closure(
        self,
        creadas,
        errores,
        *,
        operation_name: str,
        correlation_id: str | None = None,
    ) -> None:
        return show_confirmation_closure(
            self,
            creadas,
            errores,
            operation_name=operation_name,
            correlation_id=correlation_id,
        )

    def _show_pdf_actions_dialog(self, generated_path) -> None:
        return show_pdf_actions_dialog(self, generated_path)

    def _show_error_detail(self, title: str, message: str, details: str) -> None:
        from app.ui.qt_compat import QMessageBox

        detalle = f"{message}\n\n{details}" if details else message
        QMessageBox.critical(self, title, detalle)

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
        self._solicitudes_controller.aplicar_confirmacion(
            confirmadas_ids, pendientes_restantes
        )
        self._reload_pending_views()
        self._refresh_historico()
        self._refresh_saldos()
        if errores:
            self.toast.warning(
                "\n".join(errores), title=copy_text("ui.validacion.validacion")
            )

    def _on_open_saldos_modal(self) -> None:
        from . import acciones_personas

        return acciones_personas.on_open_saldos_modal(self)

    def _on_completo_changed(
        self, checked: object = False, *_args: object, **_kwargs: object
    ) -> None:
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

    def _limpiar_formulario(self) -> None:
        from . import form_handlers

        return form_handlers.limpiar_formulario(self)

    def _clear_form(self) -> None:
        from . import form_handlers

        return form_handlers.clear_form(self)

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
        if hasattr(self, "_sync_pending_select_all_visible_state"):
            self._sync_pending_select_all_visible_state()
        if getattr(self, "_pending_bulk_selection_in_progress", False):
            return
        self._refrescar_estado_operativa("pendiente_selected")

    def _prompt_confirm_pdf_path(self, selected: object) -> str | None:
        from pathlib import Path

        from app.ui.qt_compat import QFileDialog
        from app.ui.vistas.confirmacion_adaptador_qt import (
            resolver_colision_destino_pdf,
        )

        if not isinstance(selected, list) or not selected:
            return None

        sugerir_nombre = getattr(self._servicio_destino_pdf_confirmacion, "sugerir_nombre_pdf", None)
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
        logger.info(
            "UI_PENDIENTES_VER_TODAS_TOGGLE",
            extra={
                "checked": bool(checked),
                "hidden_previas": len(getattr(self, "_hidden_pendientes", [])),
                "pendientes_visibles_previas": len(
                    getattr(self, "_pending_solicitudes", [])
                ),
                "pendientes_totales_previas": len(
                    getattr(self, "_pending_all_solicitudes", [])
                ),
            },
        )
        self._pending_view_all = checked
        self._pending_selection_anchor_row = None
        self._reload_pending_views()

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

    def _sincronizar_con_confirmacion(self) -> None:
        return acciones_sincronizacion.sincronizar_con_confirmacion(self)

    def _on_sync_with_confirmation(self) -> None:
        return acciones_sincronizacion.on_sync_with_confirmation(self)

    def _verificar_handlers_ui(self) -> None:
        faltantes = [
            nombre
            for nombre in HANDLERS_UI_CRITICOS
            if not callable(getattr(self, nombre, None))
        ]
        if not faltantes:
            return

        detalle = ", ".join(faltantes)
        logger.error(
            "UI_MAINWINDOW_HANDLERS_UI_INVALIDOS",
            extra={"handlers_faltantes": faltantes},
        )
        raise RuntimeError(
            "Contrato UI MainWindow inválido. Handlers críticos ausentes o no callables: "
            f"{detalle}"
        )

    def _run_preconfirm_checks(self) -> bool:
        return validacion_preventiva._run_preconfirm_checks(self)

    def _on_sync(self) -> None:
        return acciones_sincronizacion.on_sync(self)

    def _on_push_now(self) -> None:
        return acciones_sincronizacion.on_push_now(self)

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

    def _set_config_incomplete_state(self) -> None:
        logger.info(
            "UI_MAINWINDOW_SYNC_CONFIG_INCOMPLETA_INICIO",
            extra={"evento": "init_config_incompleta"},
        )
        try:
            acciones_sincronizacion.set_config_incomplete_state(self)
            logger.info(
                "UI_MAINWINDOW_SYNC_CONFIG_INCOMPLETA_APLICADA",
                extra={"evento": "init_config_incompleta"},
            )
        except Exception as exc:
            log_operational_error(
                logger,
                "UI_MAINWINDOW_SYNC_CONFIG_INCOMPLETA_ERROR",
                exc=exc,
                extra={"evento": "init_config_incompleta"},
            )
            raise

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
