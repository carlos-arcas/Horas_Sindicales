# Features pendientes

## FTR-012 - Corregir imports Qt/headless que rompen gate_pr
- Estado: **TODO**
- Tipo: `INFRA`
- Tests:
  - `tests/golden/botones/test_boton_sync_golden.py`
  - `tests/test_presentacion_i18n_headless_import.py`
  - `tests/test_ui_import_smoke.py`
- Notas: Prioridad 1 (wiring/tests rotos). Reproducido con python -m scripts.gate_pr en entorno provisionado: PySide6.QtCore.__spec__ is None al importar presentacion.i18n.gestor_i18n en headless y ImportError de QFileDialog en app.ui.vistas.confirmacion_adaptador_qt. Mantener el fix atomico sobre imports/compatibilidad Qt sin mezclar hardcodes, naming o complejidad.

## FTR-013 - Eliminar nuevos strings hardcoded detectados en app/ui
- Estado: **TODO**
- Tipo: `UI`
- Tests:
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
- Notas: Prioridad 3 (bug pequeno). Dividir en subtareas si supera 300 LOC netas o 10 archivos. Cierre: caso reproducible cubierto por test existente o nuevo test unitario focalizado.

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
- Estado: **TODO**
- Tipo: `INFRA`
- Tests:
  - `tests/test_docs_minimas.py`
  - `tests/test_windows_scripts_contract.py`
  - `tests/test_launcher_bat_contract.py`
  - `tests/test_definicion_producto_final_contract.py`
- Notas: Prioridad 6 (cierre real de producto). Sigue siendo obligatoria la validacion manual descrita en docs/validacion_windows_real.md, pero deja de ser la siguiente tarea mientras python -m scripts.gate_pr siga rojo. Retomar solo cuando el gate canónico vuelva a verde.
