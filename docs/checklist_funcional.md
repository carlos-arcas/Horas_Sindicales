# Checklist funcional verificable

Este checklist funciona como mapa operativo del producto y como base auditable para construir pruebas E2E futuras.

## Criterios de lectura

- Una función **no** se considera hecha solo porque exista código o un botón.
- El estado global se deriva del desglose de evidencia por: lógica, UI, validaciones/seguridad y E2E.
- Si hay duda, se prioriza **Parcial** o **No verificada** para mantener veracidad.

## Estados permitidos

- Verificada
- Parcial
- No verificada
- No implementada

## Ruta crítica principal

Flujo mínimo para que el producto sea usable:

1. **FUN-001** — Lanzar aplicación.
2. **FUN-002** — Crear/validar solicitud sindical.
3. **FUN-003** — Confirmar operación y generar PDF.
4. **FUN-004** — Consultar histórico.
5. **FUN-005** — Sincronizar con Google Sheets.

## Inventario funcional

| ID | Función (lenguaje humano) | Prioridad | Estado global | Evidencia actual | Observaciones/Bloqueos |
|---|---|---|---|---|---|
| FUN-001 | Se puede lanzar la aplicación por entrypoint Python y por launcher de Windows. | Alta | Parcial | `tests/test___main___smoke.py`, `tests/ui/test_ui_smoke_startup.py`, `tests/test_launcher_bat_contract.py`, `docs/validacion_windows_real.md` | Existe evidencia estructural y smoke, pero la ejecución real en Windows sigue pendiente; no debe marcarse como completada hasta registrar esa validación manual con evidencia auditable. |
| FUN-002 | Se puede crear y validar una solicitud sindical evitando inconsistencias básicas. | Alta | Verificada | `tests/application/test_crear_solicitud_resultado.py`, `tests/application/solicitudes/test_validacion_basica.py`, `tests/application/test_solicitud_duplicate_key.py`, `tests/golden/botones/test_boton_aniadir_pendiente_golden.py` | La lógica está fuerte; falta más evidencia E2E de interacción completa de usuario. |
| FUN-003 | Se puede confirmar una solicitud y generar/exportar PDF de confirmación e histórico. | Alta | Verificada | `tests/application/test_confirmar_pdf_caso_uso.py`, `tests/ui/test_confirmar_pdf_flow.py`, `tests/e2e/test_flujo_solicitud_pdf_historico.py`, `tests/e2e/test_exportacion_pdf_historico_e2e.py` | Seguridad específica de archivos/PDF puede endurecerse más. |
| FUN-004 | Se puede consultar y filtrar el histórico de solicitudes, incluyendo borrado desde UI. | Alta | Verificada | `tests/application/test_solicitudes_historico_use_case.py`, `tests/domain/test_reglas_filtrado_historico.py`, `tests/ui/test_historico_view_model.py`, `tests/ui/test_historico_borrado.py` | Faltan más E2E de filtros complejos y escenarios con volumen alto. |
| FUN-005 | Se puede sincronizar con Google Sheets (preflight, conflictos, reporte). | Alta | Parcial | `tests/application/test_sync_sheets_use_case_scenarios.py`, `tests/application/test_sync_preflight_permissions.py`, `tests/e2e_sync/test_sync_sheets_e2e.py`, `tests/ui/test_sync_button_state_rules.py` | En inventario de features existente está como WIP; no se marca verificada. |
| FUN-006 | Se puede ejecutar auditoría E2E por CLI en dry-run y en modo con escritura de evidencias. | Media | Verificada | `tests/e2e/test_cli_auditoria_smoke.py`, `tests/integration/test_auditoria_e2e_dry_run_no_writes.py`, `tests/e2e/test_auditoria_e2e_writes_reports.py` | No aplica UI de escritorio; es una función de CLI operacional. |
| FUN-007 | Se puede gestionar el catálogo local de personajes del proyecto actual desde casos de uso de escritorio. | Media | Parcial | `tests/application/personajes/test_casos_uso_personajes.py`, `tests/domain/personajes/test_servicios_personaje.py`, `docs/features.json` | Alcance local y de escritorio; todavía no hay UI específica ni evidencia E2E dedicada. |

## Decisiones técnicas aplicadas

- Se usa `docs/checklist_funcional.json` como **fuente estructurada verificable** por máquina.
- Se mantiene `docs/checklist_funcional.md` como versión humana para revisión funcional y auditoría.
- El contrato automático valida estructura y consistencia de IDs/estados, sin afirmar la verdad funcional de cada ítem.
