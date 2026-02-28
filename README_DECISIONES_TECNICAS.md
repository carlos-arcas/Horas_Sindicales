# README_DECISIONES_TECNICAS

- Se mantuvieron APIs públicas de `SheetsSyncService`; el refactor mueve lógica pura a módulos sin cambiar contratos externos.
- El hotspot de `use_case.py` se redujo extrayendo snapshots/DTOs y reglas de reporte puras.
- `sync_snapshots.py` concentra construcción de snapshots para pull/push (DTO remoto, señales, payloads y normalización reusable).
- `sync_reporting_rules.py` centraliza reglas de resumen/reporting y textos críticos por `reason_code` estable.
- `use_case.py` queda más orientado a orquestación/wiring (runner/planner/builder + persistencia).
- Se preservó el orden estable del resumen de pull mediante `pull_stats_tuple`.
- Se preservó semántica de conflictos y reason codes críticos (`conflict_divergent`, `duplicate_without_uuid`, etc.).
- No se añadieron dependencias externas; solo reorganización interna + pruebas.
- Se aumentó cobertura headless con tests granulares de módulos puros para acelerar feedback local.
- Las pruebas de contrato validan que `use_case.py` delega en los nuevos módulos (evita regresión por “reacoplar” lógica).
- **Prueba 1 (planner puro):** `app/application/use_cases/sync_sheets/pull_planner.py` + `tests/application/test_pull_planner.py`.
- **Prueba 2 (builder puro):** `app/application/use_cases/sync_sheets/push_builder.py` + `tests/application/test_push_builder.py`.
- **Prueba 3 (nuevo refactor):** `app/application/use_cases/sync_sheets/sync_snapshots.py`, `app/application/use_cases/sync_sheets/sync_reporting_rules.py` + tests dedicados.
- Los targets de complejidad (CC) se controlan con `cc_targets` para fijar presupuestos por símbolo y hacer el refactor defendible/medible.
- CI es la fuente de verdad porque ejecuta quality gate reproducible, con entorno consistente y artefactos verificables (`quality_report`).
