# Features pendientes

## FTR-019 - Ocultar estado operativo redundante y omitir refresh del historico oculto
- Estado: **TODO**
- Tipo: `UI`
- Tests:
  - `tests/presentacion/test_ui_operativa_pendientes_contract.py`
  - `tests/presentacion/test_ui_operativa_status_panel_hidden.py`
  - `tests/ui/test_historico_refresh_hidden_skip.py`
- Notas: Prioridad 3 (bug pequeno reproducible). El backlog quedo desalineado: en este worktree hay cambios parciales de UI no reflejados en docs/features.json. Ejecutar solo la subfeature minima: ocultar panel/tips de operativa cuando no aportan senal visible y evitar refresh_historico si la pestana Historico no esta activa, sin mezclar launcher, read-only ni otros ajustes locales.
  - `tests/test_ui_strings_guard.py`
- Notas: Prioridad 2 (guardrail bajo riesgo). Reproducido con python -m scripts.gate_pr; offenders actuales en historico_actions.py y modulos de main_window. Cierre: mover texto visible a i18n y dejar solo claves no visibles cuando aplique.

## FTR-014 - Eliminar regresion de naming debt en qt_harness
- Estado: **TODO**
- Tipo: `INFRA`
- Tests:
  - `tests/test_naming_debt_guard.py`
- Notas: Prioridad 2 (guardrail bajo riesgo). Reproducido con python -m scripts.gate_pr; nuevo offender: app/testing/qt_harness.py::importar_qt_para_ui_real_o_skip. Cierre: renombrar a espanol tecnico o justificar baseline en el mismo PR.

## FTR-008 - Corregir bug pequeno reproducible en sincronizacion Sheets (conflictos/reporting)
- Estado: **TODO**
- Tipo: `LOGICA`
- Tests:
  - `tests/application/test_sync_sheets_use_case_scenarios.py`
  - `tests/application/test_sync_reporting_rules.py`
  - `tests/application/test_retry_and_conflict_resolution.py`
- Notas: Prioridad 2 (bug pequeno). Dividir en subtareas si supera 300 LOC netas o 10 archivos. Cierre: caso reproducible cubierto por test existente o nuevo test unitario focalizado.

## FTR-015 - Reducir complejidad contractual de ConfirmarPendientesPdfCasoUso.execute
- Estado: **TODO**
- Tipo: `LOGICA`
- Tests:
  - `tests/test_quality_gate_metrics.py`
- Notas: Prioridad 5 (deuda tecnica localizada). Reproducido con python -m scripts.gate_pr: app/application/use_cases/confirmacion_pdf/caso_uso.py:ConfirmarPendientesPdfCasoUso.execute tiene CC 26 con limite 20. Cierre: bajar la complejidad sin relajar el quality gate.

## FTR-010 - Reducir deuda tecnica localizada en pruebas de sincronizacion
- Estado: **TODO**
- Tipo: `LOGICA`
- Tests:
  - `tests/application/test_sync_sheets_core.py`
  - `tests/application/test_sync_sheets_core_expanded.py`
  - `tests/application/test_sync_sheets_refactor_smoke.py`
- Notas: Prioridad 5 (deuda tecnica pequena). Cambios pequenos y reversibles: extraer helper puro o simplificar duplicacion puntual sin refactor global.

## FTR-011 - Ejecutar validacion final en Windows real y consolidar evidencia de cierre
- Estado: **BLOCKED**
- Tipo: `INFRA`
- Tests:
  - `tests/test_docs_minimas.py`
  - `tests/test_windows_scripts_contract.py`
  - `tests/test_launcher_bat_contract.py`
  - `tests/test_definicion_producto_final_contract.py`
  - `tests/test_validacion_windows_real_contract.py`
- Notas: Prioridad 6 (cierre real de producto). BLOCKED hasta disponer de arbol limpio o snapshot identificable del commit validado y una sesion Windows real con revision visual/manual de lanzar_app.bat y launcher.bat segun docs/validacion_windows_real.md. En este worktree persisten cambios locales ajenos y el contexto de automatizacion no sustituye esa evidencia manual final.
