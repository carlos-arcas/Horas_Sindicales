# Guía de pruebas

## Objetivo

Estandarizar la ejecución de pruebas automáticas en local y en CI, con foco en reproducibilidad y cobertura.

## Ejecución en Windows (interfaz recomendada)

El repositorio incluye script oficial:

```bat
ejecutar_tests.bat
```

Este flujo prepara entorno y ejecuta la suite según la configuración vigente del proyecto.

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
