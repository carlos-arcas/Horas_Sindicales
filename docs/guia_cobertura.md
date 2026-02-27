# Guía de cobertura reproducible (local y CI)

## Pre-requisitos

1. Crear/activar entorno virtual.
2. Instalar dependencias base y de desarrollo:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## Comando estándar de cobertura CORE (sin UI)

```bash
pytest -q -m "not ui" --cov=. --cov-report=term-missing
```

## Comando recomendado con quality gate

```bash
python scripts/quality_gate.py
```

Este comando ejecuta:

1. Preflight de `pytest` y `pytest-cov`.
2. `ruff check .`
3. Tests CORE con cobertura y umbral del archivo `.config/quality_gate.json`.
4. Regeneración de `logs/quality_report.txt`.

## Troubleshooting: `pytest-cov no instalado`

### Síntoma típico

```text
pytest: error: unrecognized arguments: --cov ...
```

### Diagnóstico rápido

```bash
python -c "import pytest_cov"
```

Si falla, instala dependencias dev:

```bash
python -m pip install -r requirements-dev.txt
```

### Validación final

```bash
python -m pytest --help
```

Debe aparecer la bandera `--cov` en la ayuda de pytest.
