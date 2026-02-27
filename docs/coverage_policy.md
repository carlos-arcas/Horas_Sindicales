# Política de cobertura

## Fuente única de verdad

El umbral de cobertura del proyecto vive únicamente en `.config/quality_gate.json` bajo la clave `coverage_fail_under_core` (fallback `coverage_fail_under`).

Umbral actual CORE: **70%** (sin incluir `app/ui` en el gate bloqueante).

## Ejecución del gate

El gate de calidad se ejecuta con:

```bash
python scripts/quality_gate.py
```

Este script:

- Lee el umbral desde `.config/quality_gate.json`.
- Ejecuta `ruff check .`.
- Ejecuta `pytest -q -m "not ui"` con targets de cobertura configurables en
  `core_coverage_targets` y `--cov-fail-under=<valor>`.

## Cómo subir el umbral

Para elevar cobertura mínima:

1. Sube cobertura real en CI con nuevos tests.
2. Redondea hacia abajo el total reportado (ej: `67.3 -> 67`).
3. Abre un PR que incremente `coverage_fail_under_core` en `.config/quality_gate.json`.

## Reglas

- Prohibido hardcodear `--cov-fail-under` en CI, Makefile o scripts de release.
- El valor solo puede definirse en `.config/quality_gate.json`.
- No se baja el umbral una vez incrementado.
