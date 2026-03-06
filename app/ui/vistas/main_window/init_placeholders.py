from __future__ import annotations


def inicializar_placeholders(window) -> None:
    # Placeholders explícitos para contratos de inicialización self.* en tests estáticos.
    window.main_tabs = None
    window.persona_combo = window.fecha_input = window.desde_input = window.hasta_input = None
    window.desde_container = window.hasta_container = None
    window.desde_placeholder = window.hasta_placeholder = None
    window.completo_check = window.notas_input = None
    window.pending_errors_frame = window.pending_errors_summary = None
    window.show_help_toggle = None
    window.solicitudes_status_label = window.solicitudes_status_hint = None
    window.solicitudes_tip_1 = window.solicitudes_tip_2 = window.solicitudes_tip_3 = None
    window.solicitud_inline_error = window.delegada_field_error = window.fecha_field_error = window.tramo_field_error = None
    window.insertar_sin_pdf_button = window.confirmar_button = None
    window.agregar_button = window.eliminar_pendiente_button = window.eliminar_huerfana_button = None
    window.revisar_ocultas_button = window.ver_todas_pendientes_button = None
    window.pending_select_all_visible_check = None
    window.total_pendientes_label = window.pending_filter_warning = None
    window.pendientes_table = window.huerfanas_table = None
    window.pendientes_model = window.huerfanas_model = None
    window.huerfanas_label = None
    window.sync_button = window.confirm_sync_button = None
    window.retry_failed_button = window.simulate_sync_button = window.review_conflicts_button = None
    window.go_to_sync_config_button = window.copy_sync_report_button = None
    window.sync_progress = window.sync_panel_status = None
    window.sync_status_label = window.sync_status_badge = None
    window.sync_counts_label = window.sync_details_button = None
    window.sync_source_label = window.sync_scope_label = window.sync_idempotency_label = None
    window.last_sync_metrics_label = window.conflicts_reminder_label = None
    window.historico_search_input = window.historico_estado_combo = window.historico_delegada_combo = None
    window.historico_desde_date = window.historico_hasta_date = None
    window.historico_apply_filters_button = None
    window._historico_filtro_timer = None
    window._historico_filters_wired = False
    window.historico_periodo_anual_radio = window.historico_periodo_mes_radio = window.historico_periodo_rango_radio = None
    window.historico_periodo_anual_spin = window.historico_periodo_mes_ano_spin = window.historico_periodo_mes_combo = None
    window.historico_table = window.historico_model = window.historico_proxy_model = None
    window.historico_empty_state = window.historico_details_content = None
    window.open_saldos_modal_button = None
    window.generar_pdf_button = window.eliminar_button = None
    window.historico_select_all_visible_check = window.historico_sync_button = None
    window.historico_export_hint_label = None
    window.editar_pdf_button = window.abrir_pdf_check = window.goto_existing_button = None
    window.total_preview_input = None
    window.add_persona_button = window.edit_persona_button = window.delete_persona_button = None
    window.edit_grupo_button = window.opciones_button = window.config_delegada_combo = None
    window.preferencia_pantalla_completa_check = None
    window.cuadrante_warning_label = None
