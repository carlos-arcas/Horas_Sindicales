# Features pendientes

## FTR-011 - Ejecutar validacion final en Windows real y consolidar evidencia de cierre
- Estado: **TODO**
- Tipo: `INFRA`
- Tests:
  - `tests/test_docs_minimas.py`
  - `tests/test_windows_scripts_contract.py`
  - `tests/test_launcher_bat_contract.py`
  - `tests/test_definicion_producto_final_contract.py`
- Notas: Prioridad 1 (bloqueo real de producto). Ejecutar el paquete de docs/validacion_windows_real.md en una maquina Windows real y registrar evidencia bajo logs/windows_real/<run_id>. Cierre: pasos 0-8 con evidencia auditable y dictamen honesto PASS/FAIL/WARNING.

## FTR-006 - Revalidar gate rapido en entorno provisionado y corregir solo si hay fallo real
- Estado: **TODO**
- Tipo: `INFRA`
- Tests:
  - `tests/test_quality_gate_script_contract.py`
  - `tests/test_architecture_imports.py`
  - `tests/test_clean_architecture_imports_guard.py`
- Notas: Prioridad 3 (guardrail local). Primero provisionar el entorno soportado por el repo (setup.bat o .venv con requirements-dev.txt), luego reproducir python -m scripts.gate_rapido; solo si falla por bug real aplicar fix minimo sin tocar CI. Cierre: reproduccion honesta + gate rapido en verde en entorno provisionado.

## FTR-007 - Blindar sincronizacion de inventario de features nativo
- Estado: **TODO**
- Tipo: `INFRA`
- Tests:
  - `tests/tools/test_gate_pr.py`
  - `tests/test_repo_legacy_cleanup_guardrails.py`
- Notas: Prioridad 1 (guardrail bajo riesgo). Verificar que docs/features.md y docs/features_pendientes.md se regeneran de forma determinista desde docs/features.json con `python -m scripts.features_sync`. Cierre: ejecutar sync y `pytest -q tests/test_repo_legacy_cleanup_guardrails.py` en verde.

## FTR-008 - Corregir bug pequeno reproducible en sincronizacion Sheets (conflictos/reporting)
- Estado: **TODO**
- Tipo: `LOGICA`
- Tests:
  - `tests/application/test_sync_sheets_use_case_scenarios.py`
  - `tests/application/test_sync_reporting_rules.py`
  - `tests/application/test_retry_and_conflict_resolution.py`
- Notas: Prioridad 2 (bug pequeno). Dividir en subtareas si supera 300 LOC netas o 10 archivos. Cierre: caso reproducible cubierto por test existente o nuevo test unitario focalizado.

## FTR-009 - Alinear documentacion contractual de features con estado real
- Estado: **TODO**
- Tipo: `INFRA`
- Tests:
  - `tests/tools/test_gate_pr.py`
  - `tests/test_docs_minimas.py`
- Notas: Prioridad 3 (doc contractual). Mantener docs/features.json como fuente unica; regenerar derivados y evitar sistemas paralelos de roadmap o bitacora.

## FTR-010 - Reducir deuda tecnica localizada en pruebas de sincronizacion
- Estado: **TODO**
- Tipo: `LOGICA`
- Tests:
  - `tests/application/test_sync_sheets_core.py`
  - `tests/application/test_sync_sheets_core_expanded.py`
  - `tests/application/test_sync_sheets_refactor_smoke.py`
- Notas: Prioridad 4 (deuda tecnica pequena). Cambios pequenos y reversibles: extraer helper puro o simplificar duplicacion puntual sin refactor global.
