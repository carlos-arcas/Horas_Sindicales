# Política de cobertura CORE

## Contrato de cobertura

La fuente única de verdad del quality gate es `.config/quality_gate.json`.

- Clave activa: `coverage_fail_under_core`.
- Fallback de compatibilidad: `coverage_fail_under`.
- Umbral actual (fase 1): **80%**.
- Objetivo contractual final: **85%**.

Roadmap incremental del umbral:

1. **80%** (PR#1: setup + contrato + documentación)
2. **83%** (PR#2: subida con batería de tests adicional)
3. **85%** (objetivo final de portfolio)

## Qué incluye CORE

El cálculo CORE se limita a las capas no UI definidas en `core_coverage_targets`:

- `app/domain`
- `app/application`
- `app/infrastructure`
- `app/bootstrap`
- `app/configuracion`
- `app/core`
- `app/entrypoints`
- `app/pdf`

Regla: `app/ui` queda fuera del umbral bloqueante CORE.

## Ejecución reproducible

### CLI (Windows/Linux/macOS)

```bash
python scripts/quality_gate.py
```

### Windows (doble clic)

```bat
quality_gate.bat
```

### Flujo de tests recomendado en Windows

```bat
ejecutar_tests.bat
menu_validacion.bat
```

## Fallos de prerequisitos (mensaje esperado)

El script `scripts/quality_gate.py` valida prerequisitos antes de correr `pytest --cov`:

1. Comprueba que `pytest` esté instalado.
2. Comprueba que `pytest-cov` esté disponible.

Si falta `pytest-cov`, aborta con código distinto de 0 y mensaje claro:

> `Falta pytest-cov. Instala dependencias dev: pip install -r requirements-dev.txt`

## Recuperación ante fallo por dependencias

1. Activar entorno virtual.
2. Instalar dependencias base y dev:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. Reejecutar `python scripts/quality_gate.py`.
