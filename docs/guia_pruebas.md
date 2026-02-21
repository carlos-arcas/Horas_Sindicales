# Guía de pruebas

## Objetivo

Estandarizar la ejecución de pruebas automáticas en local y en CI, con foco en reproducibilidad y cobertura.

## Ejecución en Windows (interfaz recomendada)

El repositorio incluye script oficial:

```bat
ejecutar_tests.bat
```

Este flujo prepara entorno y ejecuta la suite según la configuración vigente del proyecto.

## Uso rápido: launcher.bat

Para operación manual por doble clic en Windows, usar:

```bat
launcher.bat
```

Opciones del menú operativo:

1. **Lanzar app**: delega en `lanzar_app.bat`.
2. **Ejecutar tests**: delega en `ejecutar_tests.bat`.
3. **Quality gate**: delega en `quality_gate.bat`.
4. **Auditor E2E (dry-run)**: ejecuta auditoría sin escritura (`--dry-run`).
5. **Auditor E2E (write)**: ejecuta auditoría con escritura (`--write`).
0. **Salir**.

El launcher informa la carpeta de logs (`logs\`) y muestra `PASS`/`FAIL` por opción según el exit code devuelto por cada script.

## Ejecución manual equivalente

Desde la raíz del repositorio:

```bash
PYTHONPATH=. pytest -q
```

## Cobertura

Para medir cobertura explícitamente, usar `pytest` con `--cov`:

```bash
PYTHONPATH=. pytest -q --cov=app --cov-report=term-missing
```

Si se usa quality gate, este comando puede complementarse con los scripts de `Makefile`/pipeline del proyecto.

## Markers (incluyendo UI)

- Suite completa: `pytest -q`
- Solo UI: `pytest -m ui`
- Excluir UI: `pytest -m "not ui"`

Los tests UI pueden requerir entorno gráfico o modo `offscreen` según plataforma.

## Recomendaciones de estabilidad

1. Instalar dependencias desde `requirements-dev.txt`.
2. Ejecutar primero smoke tests y luego suite completa cuando haya cambios amplios.
3. Mantener consistencia entre comandos locales y los usados por CI.

## Pendiente de completar

- Pendiente de completar matriz de tiempos objetivo por tipo de suite (smoke, unit, integración, UI).

## Validación total: quality_gate.bat

Para una validación "Nivel 4" con un único comando en Windows:

```bat
quality_gate.bat
```

El script realiza, en orden:
1. Preparación de `.venv` e instalación de `requirements-dev.txt`.
2. Auditoría E2E en modo dry-run: `python -m app.entrypoints.cli_auditoria --dry-run`.
3. Tests con cobertura y umbral mínimo: `pytest --cov=. --cov-report=term-missing --cov-fail-under=85`.

También genera logs en `logs\quality_gate_stdout.log`, `logs\quality_gate_stderr.log` y `logs\quality_gate_debug.log`, e informa al final `QUALITY GATE: PASS` o `QUALITY GATE: FAIL`.

## Snapshot/Golden tests (Auditor E2E)

Los snapshots de reportes del auditor viven en `tests/golden/` y se validan con:

```bash
PYTHONPATH=. pytest -q tests/e2e/test_auditoria_e2e_snapshot_md.py tests/e2e/test_auditoria_e2e_snapshot_json.py tests/e2e/test_auditoria_e2e_snapshot_manifest_json.py
```

### Política de actualización de golden

Por defecto, los tests **solo comparan** contra los golden existentes.

Para actualizar snapshots de forma explícita y controlada:

```bash
UPDATE_GOLDEN=1 PYTHONPATH=. pytest -q tests/e2e/test_auditoria_e2e_snapshot_md.py tests/e2e/test_auditoria_e2e_snapshot_json.py tests/e2e/test_auditoria_e2e_snapshot_manifest_json.py
```

Reglas anti-flakiness aplicadas por normalización (`tests/utilidades/normalizar_reportes.py`):
- IDs dinámicos (UUID/AUD-*) → `<ID>`.
- Fechas ISO → `<FECHA>`.
- Rutas absolutas → `<RUTA>`.
- Orden determinista de listas con `id_check`.
