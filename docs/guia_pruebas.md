# Guía de pruebas

## Propósito

Esta guía fija cómo validar la aplicación desktop **Python + PySide6** sin inventar flujos web ni comandos paralelos. El contrato del repositorio es simple: primero feedback rápido, después gate completo, y siempre con pruebas reproducibles.

## Comandos canónicos

### Gate rápido

```bash
python -m scripts.gate_rapido
```

Úsalo cuando toques lógica core, wiring o documentación contractual y necesites una señal rápida.

### Gate de PR

```bash
python -m scripts.gate_pr
```

Es el único gate contractual para cerrar cambios y el mismo que debe ejecutar CI.

## Suites por objetivo

### Núcleo de negocio

```bash
pytest -q tests/domain tests/application
```

Cobertura contractual del core:

```bash
pytest -q tests/domain tests/application   --cov=app/domain   --cov=app/application   --cov-report=term-missing   --cov-fail-under=85
```

### Suite no UI del repositorio

```bash
pytest -q -m "not ui"
```

Sirve para comprobar regresiones funcionales sin depender de un backend gráfico real.

### Golden UI

```bash
pytest -q tests/golden/botones
```

Actualización explícita de snapshots:

```bash
UPDATE_GOLDEN=1 pytest -q tests/golden/botones
```

### Guardarraíles estructurales

```bash
pytest -q   tests/test_repo_legacy_cleanup_guardrails.py   tests/test_architecture_imports.py   tests/test_clean_architecture_imports_guard.py
```

Estos tests impiden que reaparezcan referencias a stack web ajeno, archivos legacy obvios o roturas de capas.

## Flujo recomendado de validación

1. Instalar dependencias desde `requirements-dev.txt`.
2. Ejecutar `python -m scripts.gate_rapido` mientras el cambio está en curso.
3. Ejecutar pruebas focales de la zona tocada.
4. Ejecutar `python -m scripts.gate_pr` antes de cerrar.
5. Si falla, corregir y repetir; no abrir PR con el gate rojo.

## Tiempos objetivo orientativos

No son métricas de marketing; sirven para detectar cuando una suite se volvió desproporcionada:

- **Core unitario (`tests/domain`, `tests/application`)**: debería responder en segundos.
- **Suite `not ui`**: debería seguir siendo apta para uso frecuente durante desarrollo.
- **Golden UI**: debe ser determinista y mucho más barata que un smoke gráfico real.
- **Gate PR**: puede tardar más, pero debe seguir siendo ejecutable localmente sin pasos manuales ocultos.

Si alguna franja se degrada de forma sostenida, hay que revisar duplicación, setup innecesario o acoplamiento accidental.

## Validación Windows

### Script contractual de tests

```bat
ejecutar_tests.bat
```

Debe dejar cobertura, logs y resumen de ejecución en `logs/`.

### Gate operativo completo en Windows

```bat
quality_gate.bat
```

Ese script prepara entorno, ejecuta preflight, smoke contractual y cobertura para operadores Windows.

## Dependencias que no deben faltar

- `pytest`
- `pytest-cov`
- `ruff`
- `radon`
- `pytest-qt` para suites UI reales

La nota práctica es simple: instala `requirements-dev.txt` y evita entornos a medias.

## Auditoría E2E

Para generar evidencia auditable del producto:

```bash
python -m app.entrypoints.cli_auditoria --dry-run
python -m app.entrypoints.cli_auditoria --write
```

Los artefactos válidos salen en `logs/evidencias/<ID>/`.

## Qué no hacer

- No sustituir `python -m scripts.gate_pr` por scripts ad hoc.
- No mezclar resultados UI manuales con evidencias automáticas sin dejar rastro.
- No aceptar suites inestables basadas en sleeps o estado global implícito.
- No meter lógica de negocio en tests UI cuando puede cubrirse de forma pura en dominio/aplicación.
