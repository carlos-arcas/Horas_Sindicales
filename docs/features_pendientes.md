# Features pendientes

## FTR-002 - Sincronización con Google Sheets
- Estado: **WIP**
- Tipo: `INFRA`
- Tests:
  - `tests/application/test_sync_sheets_use_case_scenarios.py`
  - `tests/application/use_cases/sync_sheets/test_sync_sheets_use_case_planning.py`
- Notas: En evolución continua para robustez de conflictos y reporting.

## FTR-005 - Vertical slice de personajes (stack Django en transición)
- Estado: **WIP**
- Tipo: `UI`
- Tests:
  - `tests/application/personajes/test_casos_uso_personajes.py`
  - `tests/domain/personajes/test_servicios_personaje.py`
  - `tests/web/test_personajes.py`
- Notas: Porting incremental con strangler, pendiente integración completa de Django runtime.
