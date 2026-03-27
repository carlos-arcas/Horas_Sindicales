# Definición de Producto Final

## Nivel declarado

**Nivel 4 — Producto profesional reproducible**.

Este documento consolida la **auditoría final de cierre de producto** y el criterio contractual para decidir si el repositorio puede declararse cerrado. La decisión no se basa en impresiones: se basa en evidencia verificable, comandos reproducibles y validación honesta del criterio de realidad Windows.

## Conclusión vigente

**Estado actual: PRODUCTO CANDIDATO A CIERRE.**

Motivo: la reproducción honesta de `python -m scripts.gate_pr` en el entorno provisionado del repo ya está en verde y el backlog técnico previo de cierre queda resuelto tras cerrar `FTR-010`. Solo sigue pendiente la validación manual final en una máquina Windows real representada por `FTR-011`, así que el estado honesto sube a **PRODUCTO CANDIDATO A CIERRE**, pero todavía no a **PRODUCTO CERRADO**.

## Entrypoints oficiales

### Windows

- `lanzar_app.bat`
- `ejecutar_tests.bat`
- `quality_gate.bat`
- `auditar_e2e.bat [--dry-run|--write]`
- `setup.bat`
- `update.bat`
- `launcher.bat`

### Python / CLI

- `python -m app`
- **Auditor E2E:** `python -m app.entrypoints.cli_auditoria --dry-run` / `python -m app.entrypoints.cli_auditoria --write`
- `python -m app.entrypoints.cli_auditoria --dry-run`
- `python -m app.entrypoints.cli_auditoria --write`
- `python -m scripts.gate_rapido`
- `python -m scripts.gate_pr`

## Resultado de auditoría final A–G

### A) Entrypoints y ejecución real — PASS

- Existe entrypoint Python principal (`python -m app`) y también `main.py` como compatibilidad de arranque.
- Los entrypoints Windows principales existen en raíz y usan rutas relativas basadas en `%~dp0`.
- `launcher.bat` centraliza la operación manual por doble clic.
- La auditoría CLI tiene comandos explícitos para dry-run y write.

**Evidencia sugerida:** `python -m app`, `python -m app.entrypoints.cli_auditoria --dry-run`, revisión de `lanzar_app.bat`, `auditar_e2e.bat` y `launcher.bat`.

### B) Scripts Windows — PASS con pendiente manual de ejecución real

- Existen y son coherentes `lanzar_app.bat`, `ejecutar_tests.bat`, `quality_gate.bat`, `setup.bat`, `update.bat`, `launcher.bat` y `auditar_e2e.bat`.
- Todos preparan o consumen `.venv`, usan rutas relativas, generan logs y apuntan a entrypoints reales del repo.
- La ejecución funcional en Windows real sigue pendiente y debe registrarse con evidencia manual antes del cierre definitivo.

### C) Documentación mínima contractual — PASS

Documentos verificados:

- `docs/README.md`
- `docs/arquitectura.md`
- `docs/decisiones_tecnicas.md`
- `docs/guia_pruebas.md`
- `docs/guia_logging.md`
- `docs/definicion_producto_final.md`
- `docs/readonly_done_checklist.md`
- `docs/validacion_windows_real.md`

Se considera PASS porque la documentación mínima existe, es suficientemente explícita y está alineada con los entrypoints reales del repositorio.

### D) Auditoría E2E — PASS

La auditoría E2E existe y cubre:

- modo `dry-run`
- modo `write`
- salida reproducible en JSON y Markdown
- ID de auditoría
- estado global `PASS/FAIL`
- evidencias rastreables

**Comandos oficiales:**

- `python -m app.entrypoints.cli_auditoria --dry-run`
- `python -m app.entrypoints.cli_auditoria --write`

### E) Observabilidad — PASS

- Existen `logs/seguimiento.log` y compatibilidad con `logs/crashes.log`.
- La configuración operativa actual también emite `logs/crash.log` y `logs/error_operativo.log`.
- Hay rotación automática, formato JSONL y propagación de `correlation_id`.
- El criterio contractual mantiene referencia a `crashes.log` por compatibilidad con instalaciones previas y tests existentes.

### F) Versionado y trazabilidad — PASS

- Existe `VERSION`.
- Existe `CHANGELOG.md` estructurado.
- El versionado es coherente con la política SemVer del repositorio.
- El estado de cierre queda trazado en este documento y en el checklist congelado de readonly.

### G) Criterio de realidad Windows — WARNING

- Los scripts fueron auditados estructuralmente y están preparados para doble clic.
- En esta auditoría no se ha ejecutado la validación manual integral en una sesión Windows real con interacción de usuario y doble clic; este contexto de revisión no sustituye esa evidencia final aunque el host pueda ser Windows.
- Por tanto, la validación pendiente es **manual y obligatoria**.

**Conclusión del bloque G:** WARNING, no FAIL técnico del repositorio, pero sí bloqueo para declarar **PRODUCTO CERRADO**.

## Paquete operativo de validación Windows real

- Guía oficial: `docs/validacion_windows_real.md`
- Preparación de carpeta de evidencia: `scripts\validar_windows_real.bat`
- Mientras esa guía no se ejecute en Windows real con evidencia completa, el estado no puede subir de **PRODUCTO CANDIDATO A CIERRE**.

## Comandos de validación obligatorios

### Gate canónico

```bash
python -m scripts.gate_pr
```

### Gate rápido

```bash
python -m scripts.gate_rapido
```

### Suite focal contractual

```bash
pytest -q tests/test_docs_minimas.py tests/test_windows_scripts_contract.py tests/test_launcher_bat_contract.py tests/test_definicion_producto_final_contract.py
```

### Auditoría E2E

```bash
python -m app.entrypoints.cli_auditoria --dry-run
python -m app.entrypoints.cli_auditoria --write
```

### Cobertura contractual en Windows

```bat
ejecutar_tests.bat
```

Ese script debe ejecutar el contrato mínimo:

```bat
pytest --cov=. --cov-report=term-missing --cov-fail-under=85
```

## Evidencia disponible en el repositorio

- Tests de contratos para scripts Windows y launcher.
- Tests/documentos mínimos para arquitectura, pruebas, logging y definición de producto.
- Suite E2E para la auditoría (`tests/e2e/` y `tests/integration/`).
- Logging estructurado con `seguimiento.log`, `crash.log`, compatibilidad `crashes.log` y `correlation_id`.
- Checklist congelado de readonly en `docs/readonly_done_checklist.md`.

## Validación manual pendiente en Windows real

Ejecutar exactamente en una máquina Windows limpia siguiendo `docs/validacion_windows_real.md`:

1. `scripts\validar_windows_real.bat`
2. `setup.bat`
3. `lanzar_app.bat`
4. `ejecutar_tests.bat`
5. `quality_gate.bat`
6. `auditar_e2e.bat --dry-run`
7. `auditar_e2e.bat --write`
8. `launcher.bat`

Y confirmar:

- arranque real de la UI,
- generación de logs,
- ejecución sin pasos manuales ocultos,
- creación de evidencias de auditoría,
- consistencia de exit codes.

## Criterio de cierre

- **PRODUCTO CERRADO**: solo cuando A–G estén en PASS y además exista evidencia manual de Windows real.
- **PRODUCTO CANDIDATO A CIERRE**: cuando A–F estén en PASS, `python -m scripts.gate_pr` esté en verde y G quede pendiente únicamente por la validación manual final en una máquina Windows real.
- **PRODUCTO NO CERRADO**: si aparece cualquier FAIL real en arquitectura, scripts, auditoría E2E, observabilidad, versionado, documentación mínima o en el gate canónico de PR.

## Estado auditado en esta revisión

- A: PASS
- B: PASS
- C: PASS
- D: PASS
- E: PASS
- F: PASS
- G: WARNING
- Gate PR canónico (2026-03-27): PASS en el entorno provisionado tras cerrar `FTR-015`.
- Backlog contractual relevante: `FTR-010` queda DONE tras consolidar la cobertura de `sync_sheets_core`; `FTR-011` queda como única tarea abierta y pendiente de validación manual en Windows real.

## Cierres específicos congelados

- `docs/readonly_done_checklist.md`: evidencia auditable para declarar el alcance y estado final de readonly sin reabrir refactors cosméticos.
