# Auditoría de atributos `self.*` en `MainWindow`

## Método usado (repetible)
1. Parseo AST de `app/ui/main_window.py` para localizar `class MainWindow`.
2. Recolección de todos los accesos `self.<atributo>` en métodos de la clase.
3. Recolección de asignaciones a `self.<atributo>` **solo** en `__init__` y `_build_ui`.
4. Marcado de asignación **condicional** cuando ocurre dentro de `if` (o estructuras de control).
5. Se excluyen los métodos llamados vía `self.<método>()` (de clase/base Qt) para quedarnos con atributos de estado/UI.
6. Clasificación de riesgo: **OK**, **Condicional**, **No inicializado**.

## Resumen
- Atributos `self.*` relevantes usados en métodos: **161**.
- Riesgo **OK**: **142**.
- Riesgo **Condicional**: **0**.
- Riesgo **No inicializado**: **19**.

## Hallazgos: no inicializados en `__init__`/`_build_ui`

| Atributo | Ejemplos de uso | Riesgo |
|---|---|---|
| `_sync_thread` | `_on_push_now`:2555, `_on_push_now`:2557, `_on_push_now`:2558, `_on_push_now`:2561, `_on_push_now`:2563, `_on_push_now`:2564 | **No inicializado** |
| `_sync_worker` | `_on_push_now`:2556, `_on_push_now`:2557, `_on_push_now`:2558, `_on_push_now`:2559, `_on_push_now`:2560, `_on_push_now`:2561, … (+1) | **No inicializado** |
| `bolsa_delegada_label` | `_build_saldos_card`:468, `_build_saldos_card`:469, `_build_saldos_card`:470, `_set_bolsa_labels`:3384 | **No inicializado** |
| `bolsa_grupo_label` | `_build_saldos_card`:472, `_build_saldos_card`:473, `_build_saldos_card`:474, `_set_bolsa_labels`:3385 | **No inicializado** |
| `bolsa_mensual_label` | `_build_saldos_card`:464, `_build_saldos_card`:465, `_build_saldos_card`:466, `_set_bolsa_labels`:3383 | **No inicializado** |
| `exceso_badge` | `_build_saldos_card`:447, `_build_saldos_card`:448, `_build_saldos_card`:449, `_build_saldos_card`:452, `_set_saldos_labels`:3178, `_set_saldos_labels`:3214, … (+2) | **No inicializado** |
| `horas_input` | `_bind_manual_hours_preview_refresh`:1582, `_manual_hours_minutes`:1823 | **No inicializado** |
| `saldo_anual_consumidas` | `_build_saldos_card`:428, `_build_saldos_card`:439, `_set_saldos_labels`:3175, `_set_saldos_labels`:3199 | **No inicializado** |
| `saldo_anual_restantes` | `_build_saldos_card`:429, `_build_saldos_card`:440, `_set_saldos_labels`:3175, `_set_saldos_labels`:3200 | **No inicializado** |
| `saldo_grupo_consumidas` | `_build_saldos_card`:430, `_build_saldos_card`:443, `_set_saldos_labels`:3176, `_set_saldos_labels`:3205 | **No inicializado** |
| `saldo_grupo_restantes` | `_build_saldos_card`:431, `_build_saldos_card`:444, `_set_saldos_labels`:3176, `_set_saldos_labels`:3206 | **No inicializado** |
| `saldo_periodo_consumidas` | `_build_saldos_card`:426, `_build_saldos_card`:435, `_set_saldos_labels`:3174, `_set_saldos_labels`:3193 | **No inicializado** |
| `saldo_periodo_label` | `_build_saldos_card`:433, `_build_saldos_card`:434, `_update_periodo_label`:3165 | **No inicializado** |
| `saldo_periodo_restantes` | `_build_confirmation_payload`:2509, `_build_saldos_card`:427, `_build_saldos_card`:436, `_set_saldos_labels`:3174, `_set_saldos_labels`:3194 | **No inicializado** |
| `saldos_details_button` | `_build_saldos_card`:405, `_build_saldos_card`:406, `_build_saldos_card`:407, `_build_saldos_card`:477 | **No inicializado** |
| `saldos_details_content` | `_build_saldos_card`:409, `_build_saldos_card`:410, `_build_saldos_card`:476, `_build_saldos_card`:477 | **No inicializado** |
| `status_pending_label` | `_build_status_bar`:1241, `_build_status_bar`:1244, `_update_pending_totals`:3005 | **No inicializado** |
| `status_sync_label` | `_build_status_bar`:1235, `_build_status_bar`:1236, `_build_status_bar`:1242, `_set_sync_in_progress`:2921 | **No inicializado** |
| `status_sync_progress` | `_build_status_bar`:1237, `_build_status_bar`:1238, `_build_status_bar`:1239, `_build_status_bar`:1240, `_build_status_bar`:1243, `_set_sync_in_progress`:2922 | **No inicializado** |


## Hallazgos: inicialización condicional

- No se detectaron atributos con inicialización exclusivamente condicional.


## Inventario completo

| Atributo | Usos (método:línea) | Inicialización en `__init__`/`_build_ui` | Riesgo |
|---|---|---|---|
| `_active_sync_id` | `__init__`:320, `_on_sync`:1605, `_on_sync_failed`:1780, `_on_sync_finished`:1692, `_on_sync_finished`:1695, `_on_sync_simulation_finished`:1731 | `__init__`:320 | OK |
| `_alert_engine` | `__init__`:302, `_refresh_health_and_alerts`:3407 | `__init__`:302 | OK |
| `_alert_snooze` | `__init__`:303, `_on_snooze_alerts_today`:3458, `_refresh_health_and_alerts`:3411 | `__init__`:303 | OK |
| `_attempt_history` | `__init__`:321, `_on_sync`:1606, `_on_sync_failed`:1781, `_on_sync_finished`:1674, `_on_sync_finished`:1676, `_on_sync_finished`:1696, … (+1) | `__init__`:321 | OK |
| `_blocking_errors` | `__init__`:323, `_on_add_pendiente`:2169, `_render_preventive_validation`:1527, `_render_preventive_validation`:1528, `_render_preventive_validation`:1529, `_render_preventive_validation`:1539, … (+4) | `__init__`:323 | OK |
| `_conflict_resolution_policy` | `__init__`:318 | `__init__`:318 | OK |
| `_conflicts_service` | `__init__`:300, `_on_push_finished`:2570, `_on_review_conflicts`:1799, `_update_conflicts_reminder`:2585 | `__init__`:300 | OK |
| `_content_row` | `_build_ui`:525, `_build_ui`:526, `_build_ui`:527, `_build_ui`:531, `_update_responsive_columns`:1345, `_update_responsive_columns`:1346, … (+4) | `_build_ui`:525 | OK |
| `_duplicate_target` | `__init__`:325, `_collect_preventive_validation`:1471, `_collect_preventive_validation`:1506, `_collect_preventive_validation`:1511, `_on_go_to_existing_duplicate`:1550, `_render_preventive_validation`:1546 | `__init__`:325 | OK |
| `_field_touched` | `__init__`:322, `_mark_field_touched`:1459, `_on_add_pendiente`:2167, `_render_preventive_validation`:1527, `_render_preventive_validation`:1528, `_render_preventive_validation`:1529, … (+2) | `__init__`:322 | OK |
| `_grupo_use_cases` | `__init__`:297, `_on_edit_grupo`:1599, `_on_edit_pdf`:1817 | `__init__`:297 | OK |
| `_health_check_use_case` | `__init__`:301, `_refresh_health_and_alerts`:3399, `_refresh_health_and_alerts`:3403 | `__init__`:301 | OK |
| `_hidden_pendientes` | `__init__`:308, `_clear_pendientes`:3280, `_on_review_hidden_pendientes`:3342, `_on_review_hidden_pendientes`:3344, `_reload_pending_views`:3304, `_reload_pending_views`:3309 | `__init__`:308 | OK |
| `_historico_detail_shortcut` | `_build_ui`:1222, `_build_ui`:1223 | `_build_ui`:1222 | OK |
| `_historico_escape_shortcut` | `_build_ui`:1224, `_build_ui`:1225 | `_build_ui`:1224 | OK |
| `_historico_find_shortcut` | `_build_ui`:1220, `_build_ui`:1221 | `_build_ui`:1220 | OK |
| `_historico_group` | `_build_ui`:859 | `_build_ui`:859 | OK |
| `_historico_search_timer` | `_build_ui`:1208, `_build_ui`:1209, `_build_ui`:1210, `_build_ui`:1211, `_build_ui`:1212 | `_build_ui`:1208 | OK |
| `_last_sync_report` | `__init__`:313, `_apply_sync_report`:2678, `_on_copy_sync_report`:1657, `_on_copy_sync_report`:1659, `_on_retry_failed`:1621, `_on_show_sync_details`:1651, … (+2) | `__init__`:313 | OK |
| `_logs_dir` | `__init__`:316, `_on_open_sync_logs`:1663, `_on_open_sync_logs`:1664 | `__init__`:316 | OK |
| `_orphan_pendientes` | `__init__`:311, `_clear_pendientes`:3281, `_on_remove_huerfana`:3354, `_on_remove_huerfana`:3356, `_reload_pending_views`:3324, `_reload_pending_views`:3325, … (+1) | `__init__`:311 | OK |
| `_pdf_controller` | `__init__`:331 | `__init__`:331 | OK |
| `_pendientes_group` | `_build_ui`:718 | `_build_ui`:718 | OK |
| `_pending_all_solicitudes` | `__init__`:307, `_clear_pendientes`:3279, `_reload_pending_views`:3295, `_reload_pending_views`:3297, `_reload_pending_views`:3306 | `__init__`:307 | OK |
| `_pending_conflict_rows` | `__init__`:309, `_clear_pendientes`:3284, `_on_confirmar`:2386, `_on_insertar_sin_pdf`:2350, `_refresh_pending_conflicts`:2075, `_refresh_pending_conflicts`:2076, … (+1) | `__init__`:309 | OK |
| `_pending_solicitudes` | `__init__`:306, `_clear_pendientes`:3278, `_collect_preventive_validation`:1511, `_find_pending_duplicate_row`:2175, `_find_pending_row_by_id`:2189, `_on_remove_pendiente`:3106, … (+18) | `__init__`:306 | OK |
| `_pending_sync_plan` | `__init__`:314, `_on_confirm_sync`:1615, `_on_retry_failed`:1621, `_on_retry_failed`:1634, `_on_retry_failed`:1635, `_on_retry_failed`:1637, … (+4) | `__init__`:314 | OK |
| `_pending_view_all` | `__init__`:310, `_handle_duplicate_detected`:2268, `_on_toggle_ver_todas_pendientes`:3289, `_refresh_pending_ui_state`:2086, `_reload_pending_views`:3296, `_reload_pending_views`:3310, … (+1) | `__init__`:310 | OK |
| `_persona_use_cases` | `__init__`:295, `_load_personas`:1364, `_on_delete_persona`:2156, `_on_edit_persona`:2134 | `__init__`:295 | OK |
| `_personas` | `__init__`:305, `_build_confirmation_payload`:2496, `_current_persona`:1391, `_load_personas`:1364, `_load_personas`:1365, `_load_personas`:1374, … (+1) | `__init__`:305 | OK |
| `_personas_controller` | `__init__`:328, `_on_add_persona`:2115 | `__init__`:328 | OK |
| `_retry_sync_use_case` | `__init__`:317, `_on_retry_failed`:1637 | `__init__`:317 | OK |
| `_scroll_area` | `_build_ui`:482, `_build_ui`:483, `_build_ui`:484, `_build_ui`:485, `_build_ui`:1198, `_build_ui`:1199, … (+1) | `_build_ui`:482 | OK |
| `_settings` | `__init__`:304, `_show_optional_notice`:2963, `_show_optional_notice`:2969 | `__init__`:304 | OK |
| `_sheets_service` | `__init__`:298, `_service_account_email`:3009, `_sync_source_text`:2828 | `__init__`:298 | OK |
| `_solicitud_use_cases` | `__init__`:296, `__init__`:331, `_calculate_preview_minutes`:1862, `_collect_preventive_validation`:1497, `_collect_preventive_validation`:1499, `_collect_preventive_validation`:1503, … (+26) | `__init__`:296 | OK |
| `_solicitudes_controller` | `__init__`:329, `_on_add_pendiente`:2172 | `__init__`:329 | OK |
| `_step_bullets` | `_build_ui`:537, `_build_ui`:556, `_set_operativa_step`:1987 | `_build_ui`:537 | OK |
| `_step_titles` | `_build_ui`:538, `_build_ui`:546 | `_build_ui`:538 | OK |
| `_sync_attempts` | `__init__`:319, `_apply_sync_report`:2679, `_apply_sync_report`:2694, `_on_sync`:1607 | `__init__`:319 | OK |
| `_sync_controller` | `__init__`:330, `_on_confirm_sync`:1618, `_on_open_opciones`:1805, `_on_retry_failed`:1648, `_on_simulate_sync`:1612, `_on_sync`:1609, … (+5) | `__init__`:330 | OK |
| `_sync_in_progress` | `__init__`:312, `_set_processing_state`:2944, `_set_sync_in_progress`:2918, `_undo_confirmation`:2522 | `__init__`:312 | OK |
| `_sync_service` | `__init__`:299, `__init__`:341, `_on_confirmar`:2445, `_on_edit_grupo`:1599, `_on_edit_pdf`:1817, `_on_push_now`:2551, … (+3) | `__init__`:299 | OK |
| `_sync_started_at` | `__init__`:315, `_on_sync_failed`:1779, `_on_sync_finished`:1691, `_set_sync_in_progress`:2924 | `__init__`:315 | OK |
| `_sync_thread` | `_on_push_now`:2555, `_on_push_now`:2557, `_on_push_now`:2558, `_on_push_now`:2561, `_on_push_now`:2563, `_on_push_now`:2564 | — | No inicializado |
| `_sync_worker` | `_on_push_now`:2556, `_on_push_now`:2557, `_on_push_now`:2558, `_on_push_now`:2559, `_on_push_now`:2560, `_on_push_now`:2561, … (+1) | — | No inicializado |
| `_warnings` | `__init__`:324, `_run_preconfirm_checks`:1568, `_run_preconfirm_checks`:1569, `_run_preventive_validation`:1465 | `__init__`:324 | OK |
| `abrir_pdf_check` | `_build_ui`:811, `_build_ui`:812, `_build_ui`:813, `_on_confirmar`:2440 | `_build_ui`:811 | OK |
| `add_persona_button` | `_build_ui`:987, `_build_ui`:988, `_build_ui`:989, `_build_ui`:990, `_normalize_input_heights`:1296 | `_build_ui`:987 | OK |
| `agregar_button` | `_build_ui`:662, `_build_ui`:663, `_build_ui`:664, `_build_ui`:668, `_normalize_input_heights`:1301, `_update_action_state`:1908 | `_build_ui`:662 | OK |
| `alert_banner_label` | `_build_ui`:1163, `_build_ui`:1164, `_build_ui`:1165, `_refresh_health_and_alerts`:3401, `_render_alerts`:3430, `_render_alerts`:3433 | `_build_ui`:1163 | OK |
| `bolsa_delegada_label` | `_build_saldos_card`:468, `_build_saldos_card`:469, `_build_saldos_card`:470, `_set_bolsa_labels`:3384 | — | No inicializado |
| `bolsa_grupo_label` | `_build_saldos_card`:472, `_build_saldos_card`:473, `_build_saldos_card`:474, `_set_bolsa_labels`:3385 | — | No inicializado |
| `bolsa_mensual_label` | `_build_saldos_card`:464, `_build_saldos_card`:465, `_build_saldos_card`:466, `_set_bolsa_labels`:3383 | — | No inicializado |
| `completo_check` | `_bind_preventive_validation_events`:1456, `_build_preview_solicitud`:1837, `_build_ui`:639, `_build_ui`:640, `_build_ui`:641, `_build_ui`:711, … (+7) | `_build_ui`:639 | OK |
| `confirm_sync_button` | `_build_ui`:1059, `_build_ui`:1060, `_build_ui`:1061, `_build_ui`:1062, `_build_ui`:1063, `_on_sync`:1608, … (+3) | `_build_ui`:1059 | OK |
| `confirmar_button` | `_build_ui`:815, `_build_ui`:816, `_build_ui`:817, `_build_ui`:818, `_configure_operativa_focus_order`:1323, `_normalize_input_heights`:1305, … (+2) | `_build_ui`:815 | OK |
| `confirmation_summary_label` | `_build_ui`:572, `_build_ui`:573, `_build_ui`:574, `_build_ui`:575, `_build_ui`:576, `_update_confirmation_summary`:2010, … (+3) | `_build_ui`:572 | OK |
| `conflicts_reminder_label` | `_build_ui`:1167, `_build_ui`:1168, `_build_ui`:1169, `_build_ui`:1170, `_update_conflicts_reminder`:2586, `_update_conflicts_reminder`:2588 | `_build_ui`:1167 | OK |
| `consequence_microcopy_label` | `_build_ui`:653, `_build_ui`:654, `_build_ui`:655, `_update_solicitud_preview`:1875, `_update_solicitud_preview`:1877 | `_build_ui`:653 | OK |
| `copy_sync_report_button` | `_apply_sync_report`:2703, `_build_ui`:1077, `_build_ui`:1078, `_build_ui`:1079, `_build_ui`:1080, `_build_ui`:1081, … (+1) | `_build_ui`:1077 | OK |
| `cuadrante_warning_label` | `_build_ui`:657, `_build_ui`:658, `_build_ui`:659, `_build_ui`:660, `_collect_preventive_validation`:1519, `_update_solicitud_preview`:1880, … (+1) | `_build_ui`:657 | OK |
| `delegada_field_error` | `_build_ui`:681, `_build_ui`:682, `_build_ui`:683, `_build_ui`:684, `_render_preventive_validation`:1531, `_render_preventive_validation`:1532 | `_build_ui`:681 | OK |
| `delete_persona_button` | `_build_ui`:1008, `_build_ui`:1009, `_build_ui`:1010, `_build_ui`:1011, `_build_ui`:1012, `_normalize_input_heights`:1300, … (+1) | `_build_ui`:1008 | OK |
| `desde_container` | `_build_ui`:612, `_build_ui`:613, `_build_ui`:618, `_configure_time_placeholders`:1444, `_sync_completo_visibility`:1595 | `_build_ui`:612 | OK |
| `desde_input` | `_bind_preventive_validation_events`:1454, `_build_preview_solicitud`:1839, `_build_ui`:609, `_build_ui`:610, `_build_ui`:611, `_build_ui`:617, … (+7) | `_build_ui`:609 | OK |
| `desde_placeholder` | `_build_ui`:620, `_build_ui`:621, `_build_ui`:622, `_configure_time_placeholders`:1442, `_configure_time_placeholders`:1446 | `_build_ui`:620 | OK |
| `edit_grupo_button` | `_build_ui`:1025, `_build_ui`:1026, `_build_ui`:1027, `_build_ui`:1028, `_normalize_input_heights`:1298, `_update_action_state`:1916 | `_build_ui`:1025 | OK |
| `edit_persona_button` | `_build_ui`:992, `_build_ui`:993, `_build_ui`:994, `_build_ui`:995, `_normalize_input_heights`:1297, `_update_action_state`:1914 | `_build_ui`:992 | OK |
| `editar_pdf_button` | `_build_ui`:1030, `_build_ui`:1031, `_build_ui`:1032, `_build_ui`:1033, `_normalize_input_heights`:1303, `_update_action_state`:1917 | `_build_ui`:1030 | OK |
| `eliminar_button` | `_build_ui`:938, `_build_ui`:939, `_build_ui`:940, `_build_ui`:941, `_build_ui`:942, `_normalize_input_heights`:1307, … (+3) | `_build_ui`:938 | OK |
| `eliminar_huerfana_button` | `_build_ui`:791, `_build_ui`:792, `_build_ui`:793, `_build_ui`:794, `_build_ui`:795, `_reload_pending_views`:3329 | `_build_ui`:791 | OK |
| `eliminar_pendiente_button` | `_build_ui`:786, `_build_ui`:787, `_build_ui`:788, `_build_ui`:789, `_normalize_input_heights`:1302, `_set_processing_state`:2941, … (+1) | `_build_ui`:786 | OK |
| `exceso_badge` | `_build_saldos_card`:447, `_build_saldos_card`:448, `_build_saldos_card`:449, `_build_saldos_card`:452, `_set_saldos_labels`:3178, `_set_saldos_labels`:3214, … (+2) | — | No inicializado |
| `fecha_field_error` | `_build_ui`:686, `_build_ui`:687, `_build_ui`:688, `_build_ui`:689, `_render_preventive_validation`:1533, `_render_preventive_validation`:1534 | `_build_ui`:686 | OK |
| `fecha_input` | `_bind_preventive_validation_events`:1453, `_build_preview_solicitud`:1838, `_build_ui`:604, `_build_ui`:605, `_build_ui`:606, `_build_ui`:607, … (+6) | `_build_ui`:604 | OK |
| `generar_pdf_button` | `_build_ui`:954, `_build_ui`:955, `_build_ui`:956, `_build_ui`:957, `_normalize_input_heights`:1310, `_update_action_state`:1923, … (+1) | `_build_ui`:954 | OK |
| `go_to_sync_config_button` | `_apply_sync_report`:2701, `_build_ui`:1144, `_build_ui`:1145, `_build_ui`:1146, `_build_ui`:1147, `_build_ui`:1148, … (+1) | `_build_ui`:1144 | OK |
| `goto_existing_button` | `_build_ui`:589, `_build_ui`:590, `_build_ui`:591, `_build_ui`:592, `_build_ui`:593, `_render_preventive_validation`:1547 | `_build_ui`:589 | OK |
| `hasta_container` | `_build_ui`:627, `_build_ui`:628, `_build_ui`:633, `_configure_time_placeholders`:1445, `_sync_completo_visibility`:1596 | `_build_ui`:627 | OK |
| `hasta_input` | `_bind_preventive_validation_events`:1455, `_build_preview_solicitud`:1840, `_build_ui`:624, `_build_ui`:625, `_build_ui`:626, `_build_ui`:632, … (+7) | `_build_ui`:624 | OK |
| `hasta_placeholder` | `_build_ui`:635, `_build_ui`:636, `_build_ui`:637, `_configure_time_placeholders`:1443, `_configure_time_placeholders`:1447 | `_build_ui`:635 | OK |
| `health_checks_tree` | `_build_ui`:1176, `_build_ui`:1177, `_build_ui`:1178, `_build_ui`:1179, `_build_ui`:1180, `_render_health_report`:3416, … (+1) | `_build_ui`:1176 | OK |
| `health_summary_label` | `_build_ui`:1173, `_build_ui`:1174, `_build_ui`:1175, `_refresh_health_and_alerts`:3400, `_render_health_report`:3426 | `_build_ui`:1173 | OK |
| `historico_clear_filters_button` | `_build_ui`:905, `_build_ui`:906, `_build_ui`:907, `_build_ui`:1218, `_configure_historico_focus_order`:1331, `_configure_historico_focus_order`:1332, … (+1) | `_build_ui`:905 | OK |
| `historico_delegada_combo` | `_apply_historico_filters`:1412, `_build_ui`:879, `_build_ui`:880, `_build_ui`:882, `_build_ui`:1214, `_clear_historico_filters`:1423, … (+8) | `_build_ui`:879 | OK |
| `historico_desde_date` | `_apply_historico_filters`:1410, `_apply_historico_last_30_days`:1416, `_build_ui`:887, `_build_ui`:888, `_build_ui`:889, `_build_ui`:890, … (+5) | `_build_ui`:887 | OK |
| `historico_details_button` | `_build_ui`:852, `_build_ui`:853, `_build_ui`:854, `_build_ui`:961 | `_build_ui`:852 | OK |
| `historico_details_content` | `_build_ui`:855, `_build_ui`:856, `_build_ui`:959, `_build_ui`:962 | `_build_ui`:855 | OK |
| `historico_estado_combo` | `_apply_historico_filters`:1411, `_build_ui`:872, `_build_ui`:873, `_build_ui`:875, `_build_ui`:877, `_build_ui`:1213, … (+4) | `_build_ui`:872 | OK |
| `historico_hasta_date` | `_apply_historico_filters`:1410, `_apply_historico_last_30_days`:1417, `_build_ui`:894, `_build_ui`:895, `_build_ui`:896, `_build_ui`:897, … (+5) | `_build_ui`:894 | OK |
| `historico_last_30_button` | `_build_ui`:901, `_build_ui`:902, `_build_ui`:903, `_build_ui`:1217, `_configure_historico_focus_order`:1330, `_configure_historico_focus_order`:1331, … (+1) | `_build_ui`:901 | OK |
| `historico_model` | `_build_ui`:914, `_build_ui`:916, `_focus_historico_duplicate`:2232, `_focus_historico_duplicate`:2233, `_focus_historico_duplicate`:2237, `_load_personas`:1377, … (+4) | `_build_ui`:914 | OK |
| `historico_proxy_model` | `_apply_historico_filters`:1410, `_apply_historico_filters`:1411, `_apply_historico_filters`:1412, `_apply_historico_text_filter`:1406, `_build_ui`:915, `_build_ui`:917, … (+6) | `_build_ui`:915 | OK |
| `historico_search_input` | `_apply_historico_text_filter`:1406, `_build_ui`:867, `_build_ui`:868, `_build_ui`:870, `_build_ui`:1212, `_clear_historico_filters`:1421, … (+6) | `_build_ui`:867 | OK |
| `historico_table` | `_build_ui`:912, `_build_ui`:917, `_build_ui`:918, `_build_ui`:919, `_build_ui`:920, `_build_ui`:921, … (+15) | `_build_ui`:912 | OK |
| `historico_view_model` | `_build_ui`:913, `_build_ui`:914, `_build_ui`:915 | `_build_ui`:913 | OK |
| `horas_input` | `_bind_manual_hours_preview_refresh`:1582, `_manual_hours_minutes`:1823 | — | No inicializado |
| `huerfanas_label` | `_build_ui`:759, `_build_ui`:760, `_build_ui`:761, `_build_ui`:762, `_reload_pending_views`:3327 | `_build_ui`:759 | OK |
| `huerfanas_model` | `_build_ui`:765, `_build_ui`:766, `_clear_pendientes`:3283, `_load_personas`:1376, `_reload_pending_views`:3325 | `_build_ui`:765 | OK |
| `huerfanas_table` | `_build_ui`:764, `_build_ui`:766, `_build_ui`:767, `_build_ui`:768, `_build_ui`:769, `_build_ui`:770, … (+7) | `_build_ui`:764 | OK |
| `insertar_sin_pdf_button` | `_build_ui`:797, `_build_ui`:798, `_build_ui`:799, `_build_ui`:800, `_configure_operativa_focus_order`:1322, `_configure_operativa_focus_order`:1323, … (+2) | `_build_ui`:797 | OK |
| `last_sync_label` | `_build_ui`:1100, `_build_ui`:1101, `_build_ui`:1102, `_refresh_last_sync_label`:3472, `_refresh_last_sync_label`:3475 | `_build_ui`:1100 | OK |
| `last_sync_metrics_label` | `_apply_sync_report`:2696, `_build_ui`:1104, `_build_ui`:1105, `_build_ui`:1106 | `_build_ui`:1104 | OK |
| `main_tabs` | `_build_confirmation_payload`:2516, `_build_ui`:509, `_build_ui`:510, `_build_ui`:511, `_build_ui`:512, `_build_ui`:836, … (+5) | `_build_ui`:509 | OK |
| `notas_input` | `_build_ui`:703, `_build_ui`:704, `_build_ui`:705, `_build_ui`:706, `_build_ui`:712, `_build_ui`:713, … (+3) | `_build_ui`:703 | OK |
| `notifications` | `__init__`:327, `_on_eliminar`:3089, `_on_remove_pendiente`:3128, `_on_retry_failed`:1622, `_on_retry_failed`:1639, `_on_sync_failed`:1784, … (+2) | `__init__`:327 | OK |
| `opciones_button` | `_build_ui`:1035, `_build_ui`:1036, `_build_ui`:1037, `_build_ui`:1038, `_normalize_input_heights`:1299 | `_build_ui`:1035 | OK |
| `open_sync_logs_button` | `_build_ui`:1083, `_build_ui`:1084, `_build_ui`:1085, `_build_ui`:1086 | `_build_ui`:1083 | OK |
| `pendientes_model` | `_build_ui`:747, `_build_ui`:748, `_clear_pendientes`:3282, `_focus_pending_row`:2216, `_focus_pending_row`:2219, `_load_personas`:1375, … (+3) | `_build_ui`:747 | OK |
| `pendientes_table` | `_build_ui`:746, `_build_ui`:748, `_build_ui`:749, `_build_ui`:750, `_build_ui`:751, `_build_ui`:752, … (+12) | `_build_ui`:746 | OK |
| `pending_details_button` | `_build_ui`:731, `_build_ui`:732, `_build_ui`:733, `_build_ui`:833 | `_build_ui`:731 | OK |
| `pending_details_content` | `_build_ui`:741, `_build_ui`:742, `_build_ui`:832, `_build_ui`:833 | `_build_ui`:741 | OK |
| `pending_errors_frame` | `_build_ui`:578, `_build_ui`:579, `_build_ui`:580, `_build_ui`:594, `_build_ui`:595, `_render_preventive_validation`:1544 | `_build_ui`:578 | OK |
| `pending_errors_summary` | `_build_ui`:586, `_build_ui`:587, `_build_ui`:588, `_render_preventive_validation`:1545 | `_build_ui`:586 | OK |
| `pending_errors_title` | `_build_ui`:583, `_build_ui`:584, `_build_ui`:585 | `_build_ui`:583 | OK |
| `pending_filter_warning` | `_build_ui`:734, `_build_ui`:735, `_build_ui`:736, `_build_ui`:737, `_reload_pending_views`:3311, `_reload_pending_views`:3314, … (+1) | `_build_ui`:734 | OK |
| `persona_combo` | `_bind_preventive_validation_events`:1452, `_build_ui`:481, `_build_ui`:707, `_build_ui`:1003, `_build_ui`:1004, `_configure_operativa_focus_order`:1316, … (+10) | `_build_ui`:481 | OK |
| `primary_cta_button` | `_build_ui`:820, `_build_ui`:821, `_build_ui`:822, `_build_ui`:823, `_build_ui`:824, `_configure_operativa_focus_order`:1321, … (+13) | `_build_ui`:820 | OK |
| `primary_cta_hint` | `_build_ui`:826, `_build_ui`:827, `_build_ui`:828, `_update_action_state`:1944, `_update_action_state`:1947, `_update_action_state`:1950, … (+3) | `_build_ui`:826 | OK |
| `refresh_health_button` | `_build_ui`:1182, `_build_ui`:1183, `_build_ui`:1184, `_build_ui`:1185 | `_build_ui`:1182 | OK |
| `resync_historico_button` | `_build_ui`:949, `_build_ui`:950, `_build_ui`:951, `_build_ui`:952, `_normalize_input_heights`:1309, `_update_action_state`:1922, … (+1) | `_build_ui`:949 | OK |
| `retry_failed_button` | `_apply_sync_report`:2704, `_build_ui`:1065, `_build_ui`:1066, `_build_ui`:1067, `_build_ui`:1068, `_build_ui`:1069, … (+1) | `_build_ui`:1065 | OK |
| `review_conflicts_button` | `_apply_sync_report`:2705, `_build_ui`:1093, `_build_ui`:1094, `_build_ui`:1095, `_build_ui`:1096, `_build_ui`:1097, … (+1) | `_build_ui`:1093 | OK |
| `revisar_ocultas_button` | `_build_ui`:726, `_build_ui`:727, `_build_ui`:728, `_build_ui`:729, `_build_ui`:730, `_reload_pending_views`:3312, … (+1) | `_build_ui`:726 | OK |
| `saldo_anual_consumidas` | `_build_saldos_card`:428, `_build_saldos_card`:439, `_set_saldos_labels`:3175, `_set_saldos_labels`:3199 | — | No inicializado |
| `saldo_anual_restantes` | `_build_saldos_card`:429, `_build_saldos_card`:440, `_set_saldos_labels`:3175, `_set_saldos_labels`:3200 | — | No inicializado |
| `saldo_grupo_consumidas` | `_build_saldos_card`:430, `_build_saldos_card`:443, `_set_saldos_labels`:3176, `_set_saldos_labels`:3205 | — | No inicializado |
| `saldo_grupo_restantes` | `_build_saldos_card`:431, `_build_saldos_card`:444, `_set_saldos_labels`:3176, `_set_saldos_labels`:3206 | — | No inicializado |
| `saldo_periodo_consumidas` | `_build_saldos_card`:426, `_build_saldos_card`:435, `_set_saldos_labels`:3174, `_set_saldos_labels`:3193 | — | No inicializado |
| `saldo_periodo_label` | `_build_saldos_card`:433, `_build_saldos_card`:434, `_update_periodo_label`:3165 | — | No inicializado |
| `saldo_periodo_restantes` | `_build_confirmation_payload`:2509, `_build_saldos_card`:427, `_build_saldos_card`:436, `_set_saldos_labels`:3174, `_set_saldos_labels`:3194 | — | No inicializado |
| `saldos_details_button` | `_build_saldos_card`:405, `_build_saldos_card`:406, `_build_saldos_card`:407, `_build_saldos_card`:477 | — | No inicializado |
| `saldos_details_content` | `_build_saldos_card`:409, `_build_saldos_card`:410, `_build_saldos_card`:476, `_build_saldos_card`:477 | — | No inicializado |
| `simulate_sync_button` | `_build_ui`:1054, `_build_ui`:1055, `_build_ui`:1056, `_build_ui`:1057, `_set_sync_in_progress`:2927 | `_build_ui`:1054 | OK |
| `snooze_alerts_button` | `_build_ui`:1186, `_build_ui`:1187, `_build_ui`:1188, `_build_ui`:1189 | `_build_ui`:1186 | OK |
| `solicitud_inline_error` | `_build_ui`:676, `_build_ui`:677, `_build_ui`:678, `_build_ui`:679, `_update_solicitud_preview`:1882, `_update_solicitud_preview`:1883 | `_build_ui`:676 | OK |
| `status_pending_label` | `_build_status_bar`:1241, `_build_status_bar`:1244, `_update_pending_totals`:3005 | — | No inicializado |
| `status_sync_label` | `_build_status_bar`:1235, `_build_status_bar`:1236, `_build_status_bar`:1242, `_set_sync_in_progress`:2921 | — | No inicializado |
| `status_sync_progress` | `_build_status_bar`:1237, `_build_status_bar`:1238, `_build_status_bar`:1239, `_build_status_bar`:1240, `_build_status_bar`:1243, `_set_sync_in_progress`:2922 | — | No inicializado |
| `stepper_context_label` | `_build_ui`:568, `_build_ui`:569, `_build_ui`:570, `_update_step_context`:2006 | `_build_ui`:568 | OK |
| `stepper_labels` | `_build_ui`:536, `_build_ui`:561, `_set_operativa_step`:1977, `_update_action_state`:1931, `_update_action_state`:1933 | `_build_ui`:536 | OK |
| `sync_button` | `_build_ui`:1049, `_build_ui`:1050, `_build_ui`:1051, `_build_ui`:1052, `_set_sync_in_progress`:2926 | `_build_ui`:1049 | OK |
| `sync_counts_label` | `_apply_sync_report`:2685, `_build_ui`:1140, `_build_ui`:1141, `_build_ui`:1142 | `_build_ui`:1140 | OK |
| `sync_details_button` | `_apply_sync_report`:2702, `_build_ui`:1071, `_build_ui`:1072, `_build_ui`:1073, `_build_ui`:1074, `_build_ui`:1075, … (+1) | `_build_ui`:1071 | OK |
| `sync_history_button` | `_build_ui`:1088, `_build_ui`:1089, `_build_ui`:1090, `_build_ui`:1091 | `_build_ui`:1088 | OK |
| `sync_idempotency_label` | `__init__`:340, `_apply_sync_report`:2684, `_build_ui`:1136, `_build_ui`:1137, `_build_ui`:1138 | `_build_ui`:1136 | OK |
| `sync_panel_status` | `_apply_sync_report`:2693, `_build_ui`:1124, `_build_ui`:1125, `_build_ui`:1126, `_set_sync_in_progress`:2933 | `_build_ui`:1124 | OK |
| `sync_progress` | `_build_ui`:1153, `_build_ui`:1154, `_build_ui`:1155, `_build_ui`:1156, `_build_ui`:1160, `_set_sync_in_progress`:2920 | `_build_ui`:1153 | OK |
| `sync_scope_label` | `__init__`:339, `_apply_sync_report`:2683, `_build_ui`:1132, `_build_ui`:1133, `_build_ui`:1134 | `_build_ui`:1132 | OK |
| `sync_source_label` | `__init__`:338, `_apply_sync_report`:2682, `_build_ui`:1128, `_build_ui`:1129, `_build_ui`:1130 | `_build_ui`:1128 | OK |
| `sync_status_badge` | `_build_ui`:1117, `_build_ui`:1118, `_build_ui`:1119, `_build_ui`:1120, `_set_sync_status_badge`:2799, `_set_sync_status_badge`:2801, … (+5) | `_build_ui`:1117 | OK |
| `sync_status_label` | `_build_ui`:1150, `_build_ui`:1151, `_build_ui`:1152, `_build_ui`:1159, `_set_sync_in_progress`:2919 | `_build_ui`:1150 | OK |
| `sync_trend_label` | `_build_ui`:1108, `_build_ui`:1109, `_build_ui`:1110, `_refresh_sync_trend_label`:3464, `_refresh_sync_trend_label`:3467 | `_build_ui`:1108 | OK |
| `toast` | `__init__`:326, `__init__`:327, `__init__`:335, `_on_add_pendiente`:2170, `_on_confirm_sync`:1616, `_on_confirmar`:2387, … (+33) | `__init__`:326 | OK |
| `total_pendientes_label` | `_build_ui`:807, `_build_ui`:808, `_build_ui`:809, `_update_pending_totals`:3004 | `_build_ui`:807 | OK |
| `total_preview_input` | `_build_ui`:647, `_build_ui`:648, `_build_ui`:649, `_build_ui`:650, `_build_ui`:651, `_update_solicitud_preview`:1873 | `_build_ui`:647 | OK |
| `total_preview_label` | `_build_ui`:643, `_build_ui`:644, `_build_ui`:645 | `_build_ui`:643 | OK |
| `tramo_field_error` | `_build_ui`:691, `_build_ui`:692, `_build_ui`:693, `_build_ui`:694, `_render_preventive_validation`:1535, `_render_preventive_validation`:1536 | `_build_ui`:691 | OK |
| `ver_detalle_button` | `_build_ui`:944, `_build_ui`:945, `_build_ui`:946, `_build_ui`:947, `_normalize_input_heights`:1308, `_update_action_state`:1921, … (+1) | `_build_ui`:944 | OK |
| `ver_todas_pendientes_button` | `_build_ui`:721, `_build_ui`:722, `_build_ui`:723, `_build_ui`:724, `_build_ui`:725, `_handle_duplicate_detected`:2269, … (+2) | `_build_ui`:721 | OK |
