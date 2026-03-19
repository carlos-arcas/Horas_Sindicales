# README de documentación

## Propósito

Este índice concentra la documentación contractual y operativa necesaria para auditar, ejecutar y cerrar el producto **Horas Sindicales** sin depender de conocimiento implícito.

## Documentos mínimos contractuales

- `docs/arquitectura.md`: capas vigentes, límites y diagrama ASCII.
- `docs/decisiones_tecnicas.md`: decisiones técnicas relevantes y su justificación.
- `docs/guia_pruebas.md`: comandos oficiales para tests, gate y auditoría E2E.
- `docs/guia_logging.md`: canales de logging, formato JSONL y trazabilidad.
- `docs/definicion_producto_final.md`: criterio de cierre, auditoría final A–G y conclusión vigente.
- `docs/readonly_done_checklist.md`: evidencia congelada del cierre de readonly.

## Entrypoints oficiales

### Windows

- `lanzar_app.bat`: arranque principal de la aplicación.
- `ejecutar_tests.bat`: suite contractual con cobertura.
- `quality_gate.bat`: gate operativo con preflight, auditoría dry-run y cobertura.
- `auditar_e2e.bat [--dry-run|--write]`: auditoría E2E reproducible.
- `setup.bat`: preparación inicial del entorno Windows.
- `update.bat`: actualización del entorno y dependencias en Windows.
- `launcher.bat`: menú operativo para ejecución manual por doble clic.

### Python / CLI

- `python -m app`: entrypoint Python principal.
- `python -m app.entrypoints.cli_auditoria --dry-run`: auditoría E2E sin escrituras.
- `python -m app.entrypoints.cli_auditoria --write`: auditoría E2E con generación de evidencias.
- `python -m scripts.gate_rapido`: gate rápido.
- `python -m scripts.gate_pr`: gate canónico de PR.

## Evidencia de cierre y trazabilidad

Para una auditoría final del producto, revisar en este orden:

1. `docs/definicion_producto_final.md`.
2. `docs/readonly_done_checklist.md`.
3. `CHANGELOG.md` y `VERSION`.
4. `logs/seguimiento.log`, `logs/error_operativo.log`, `logs/crash.log` y compatibilidad `logs/crashes.log`.
5. Evidencias de auditoría E2E generadas por `app.entrypoints.cli_auditoria`.

## Convención de uso

- La fuente de verdad del gate es `python -m scripts.gate_pr`.
- La política del repositorio prohíbe declarar **PRODUCTO CERRADO** sin evidencia en Windows real.
- Si el entorno actual no es Windows, el máximo estado honesto es **PRODUCTO CANDIDATO A CIERRE**, siempre que el resto de bloques estén en PASS y la validación manual pendiente quede documentada.
