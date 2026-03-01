from __future__ import annotations

from app.ui.vistas import historico_actions
from app.ui.vistas.main_window import acciones_pendientes, acciones_personas, acciones_sincronizacion, data_refresh, form_handlers, validacion_preventiva


def _wrap(fn):
    def _method(self, *args, **kwargs):
        return fn(self, *args, **kwargs)
    return _method


def registrar_state_bindings(cls) -> None:
    delegados = {
        "_limpiar_formulario": form_handlers.limpiar_formulario,
        "_is_form_dirty": acciones_personas.is_form_dirty,
        "_confirmar_cambio_delegada": acciones_personas.confirmar_cambio_delegada,
        "_save_current_draft": acciones_personas.save_current_draft,
        "_restore_draft_for_persona": acciones_personas.restore_draft_for_persona,
        "_clear_form": form_handlers.clear_form,
        "_sincronizar_con_confirmacion": acciones_sincronizacion.sincronizar_con_confirmacion,
        "_on_sync_with_confirmation": acciones_sincronizacion.on_sync_with_confirmation,
        "_on_export_historico_pdf": historico_actions.on_export_historico_pdf,
        "_normalize_input_heights": acciones_personas.normalize_input_heights,
        "_configure_operativa_focus_order": acciones_personas.configure_operativa_focus_order,
        "_configure_historico_focus_order": historico_actions.configure_historico_focus_order,
        "_update_responsive_columns": acciones_personas.update_responsive_columns,
        "_load_personas": acciones_personas.load_personas,
        "_current_persona": acciones_personas.current_persona,
        "_on_persona_changed": acciones_personas.on_persona_changed,
        "_on_config_delegada_changed": acciones_personas.on_config_delegada_changed,
        "_restaurar_contexto_guardado": acciones_personas.restaurar_contexto_guardado,
        "_selected_config_persona": acciones_personas.selected_config_persona,
        "_sync_config_persona_actions": acciones_personas.sync_config_persona_actions,
        "_apply_historico_text_filter": historico_actions.apply_historico_text_filter,
        "_historico_period_filter_state": historico_actions.historico_period_filter_state,
        "_apply_historico_filters": historico_actions.apply_historico_filters,
        "_update_historico_empty_state": historico_actions.update_historico_empty_state,
        "_apply_historico_default_range": historico_actions.apply_historico_default_range,
        "_apply_historico_last_30_days": historico_actions.apply_historico_last_30_days,
        "_on_historico_periodo_mode_changed": historico_actions.on_historico_periodo_mode_changed,
        "_on_historico_apply_filters": historico_actions.on_historico_apply_filters,
        "_on_historico_escape": historico_actions.on_historico_escape,
        "_bind_preventive_validation_events": validacion_preventiva._bind_preventive_validation_events,
        "_mark_field_touched": validacion_preventiva._mark_field_touched,
        "_schedule_preventive_validation": validacion_preventiva._schedule_preventive_validation,
        "_run_preventive_validation": validacion_preventiva._run_preventive_validation,
        "_collect_base_preventive_errors": validacion_preventiva._collect_base_preventive_errors,
        "_collect_preventive_business_rules": validacion_preventiva._collect_preventive_business_rules,
        "_collect_pending_duplicates_warning": validacion_preventiva._collect_pending_duplicates_warning,
        "_collect_preventive_validation": validacion_preventiva._collect_preventive_validation,
        "_render_preventive_validation": validacion_preventiva._render_preventive_validation,
        "_on_go_to_existing_duplicate": validacion_preventiva._on_go_to_existing_duplicate,
        "_run_preconfirm_checks": validacion_preventiva._run_preconfirm_checks,
        "_bind_manual_hours_preview_refresh": validacion_preventiva._bind_manual_hours_preview_refresh,
        "_on_sync": acciones_sincronizacion.on_sync,
        "_on_simulate_sync": acciones_sincronizacion.on_simulate_sync,
        "_on_confirm_sync": acciones_sincronizacion.on_confirm_sync,
        "_on_retry_failed": acciones_sincronizacion.on_retry_failed,
        "_on_show_sync_details": acciones_sincronizacion.on_show_sync_details,
        "_on_copy_sync_report": acciones_sincronizacion.on_copy_sync_report,
        "_on_open_sync_logs": acciones_sincronizacion.on_open_sync_logs,
        "_on_sync_finished": acciones_sincronizacion.on_sync_finished,
        "_on_sync_simulation_finished": acciones_sincronizacion.on_sync_simulation_finished,
        "_refresh_after_sync": acciones_sincronizacion.refresh_after_sync,
        "_on_sync_failed": acciones_sincronizacion.on_sync_failed,
        "_on_review_conflicts": acciones_sincronizacion.on_review_conflicts,
        "_on_open_opciones": acciones_sincronizacion.on_open_opciones,
        "_open_google_sheets_config": acciones_sincronizacion.open_google_sheets_config,
        "_set_config_incomplete_state": acciones_sincronizacion.set_config_incomplete_state,
        "_manual_hours_minutes": validacion_preventiva._manual_hours_minutes,
        "_build_preview_solicitud": form_handlers.build_preview_solicitud,
        "_calculate_preview_minutes": validacion_preventiva._calculate_preview_minutes,
        "_update_solicitud_preview": validacion_preventiva._update_solicitud_preview,
        "_validate_solicitud_form": validacion_preventiva._validate_solicitud_form,
        "_update_solicitudes_status_panel": validacion_preventiva._update_solicitudes_status_panel,
        "_focus_first_invalid_field": validacion_preventiva._focus_first_invalid_field,
        "_selected_pending_solicitudes": acciones_pendientes.helper_selected_pending_solicitudes,
        "_refresh_pending_conflicts": acciones_pendientes.helper_refresh_pending_conflicts,
        "_refresh_pending_ui_state": acciones_pendientes.helper_refresh_pending_ui_state,
        "_selected_historico": historico_actions.selected_historico,
        "_selected_historico_solicitudes": historico_actions.selected_historico_solicitudes,
        "_on_historico_select_all_visible_toggled": historico_actions.on_historico_select_all_visible_toggled,
        "_sync_historico_select_all_visible_state": historico_actions.sync_historico_select_all_visible_state,
        "_on_add_persona": acciones_personas.on_add_persona,
        "_on_edit_persona": acciones_personas.on_edit_persona,
        "_on_delete_persona": acciones_personas.on_delete_persona,
        "_selected_pending_row_indexes": acciones_pendientes.helper_selected_pending_row_indexes,
        "_selected_pending_for_editing": acciones_pendientes.helper_selected_pending_for_editing,
        "_find_pending_duplicate_row": acciones_pendientes.helper_find_pending_duplicate_row,
        "_find_pending_row_by_id": acciones_pendientes.helper_find_row_by_id,
        "_handle_duplicate_before_add": acciones_pendientes.on_handle_duplicate_before_add,
        "_focus_pending_row": acciones_pendientes.helper_focus_pending_row,
        "_focus_pending_by_id": acciones_pendientes.helper_focus_pending_by_id,
        "_focus_historico_duplicate": historico_actions.focus_historico_duplicate,
        "_resolve_pending_conflict": acciones_pendientes.on_resolve_pending_conflict,
        "_on_push_now": acciones_sincronizacion.on_push_now,
        "_on_push_finished": acciones_sincronizacion.on_push_finished,
        "_on_push_failed": acciones_sincronizacion.on_push_failed,
        "_update_sync_button_state": acciones_sincronizacion.update_sync_button_state,
        "_update_conflicts_reminder": acciones_sincronizacion.update_conflicts_reminder,
        "_show_sync_error_dialog": acciones_sincronizacion.show_sync_error_dialog,
        "_apply_sync_report": acciones_sincronizacion.apply_sync_report,
        "_on_show_sync_history": acciones_sincronizacion.on_show_sync_history,
        "_show_sync_details_dialog": acciones_sincronizacion.show_sync_details_dialog,
        "_set_sync_status_badge": acciones_sincronizacion.set_sync_status_badge,
        "_sync_source_text": acciones_sincronizacion.sync_source_text,
        "_sync_actor_text": acciones_sincronizacion.sync_actor_text,
        "_show_sync_summary_dialog": acciones_sincronizacion.show_sync_summary_dialog,
        "_notify_historico_filter_if_hidden": historico_actions.notify_historico_filter_if_hidden,
        "_update_pending_totals": acciones_pendientes.helper_update_pending_totals,
        "_service_account_email": acciones_sincronizacion.service_account_email,
        "_on_generar_pdf_historico": historico_actions.on_generar_pdf_historico,
        "_on_eliminar": historico_actions.on_eliminar,
        "_on_remove_pendiente": acciones_pendientes.on_remove_pendiente,
        "_refresh_historico": data_refresh.refresh_historico,
        "_refresh_saldos": data_refresh.refresh_saldos,
        "_on_open_historico_detalle": historico_actions.on_open_historico_detalle,
        "_pending_minutes_for_period": acciones_pendientes.helper_pending_minutes_for_period,
        "_clear_pendientes": acciones_pendientes.on_clear_pendientes,
        "_reload_pending_views": data_refresh.reload_pending_views,
        "_on_review_hidden_pendientes": acciones_pendientes.on_review_hidden,
        "_on_remove_huerfana": acciones_pendientes.on_remove_huerfana,
    }
    for name, fn in delegados.items():
        setattr(cls, name, _wrap(fn))

    cls._status_from_summary = _wrap(acciones_sincronizacion.status_from_summary)
    cls._status_to_label = staticmethod(acciones_sincronizacion.status_to_label)
    cls._sync_scope_text = staticmethod(acciones_sincronizacion.sync_scope_text)
    cls._normalize_sync_error = staticmethod(acciones_sincronizacion.normalize_sync_error)
    cls._set_sync_in_progress = _wrap(acciones_sincronizacion.set_sync_in_progress)

    from .state_helpers import set_processing_state

    def _set_processing_state(self, in_progress: bool) -> None:
        set_processing_state(self, in_progress)

    cls._set_processing_state = _set_processing_state
