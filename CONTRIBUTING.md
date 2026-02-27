# Guía de contribución

Gracias por contribuir a **Horas Sindicales**. Este documento define el flujo de trabajo y los criterios técnicos mínimos para mantener la calidad del repositorio.

## Creación de ramas

Crea siempre tu trabajo en una rama nueva a partir de `main`:

- `feature/<descripcion-corta>` para nuevas funcionalidades.
- `bugfix/<descripcion-corta>` para corrección de errores.
- `refactor/<descripcion-corta>` para cambios internos sin modificar comportamiento.

Ejemplos:

```bash
git checkout main
git pull
git checkout -b feature/sync-resumen-ui
```

## Flujo de Pull Request

- Abre PRs **pequeños y enfocados**.
- Un PR debe resolver **un problema concreto**.
- Evita cambios no relacionados en el mismo PR.
- Describe claramente el alcance, riesgo y validación realizada.

## Reglas obligatorias para merge

Para que un PR sea aceptable, debe cumplir todo lo siguiente:

- CI en verde.
- La cobertura no baja respecto al baseline.
- Ruff sin errores.
- Test de arquitectura en verde.
- Si cambia comportamiento funcional, se debe añadir o actualizar test.

## Ejecución local alineada con GitHub Actions

La CI está dividida en 2 jobs:

- `core` (obligatorio): lint + tests no-UI + coverage.
- `ui` (no bloqueante): tests de UI con `xvfb`.

Comandos locales equivalentes:

```bash
# core
ruff check .
pytest -q -m "not ui" --cov=app --cov-report=term-missing --cov-fail-under=$(python -c "import json;print(json.load(open('.config/quality_gate.json', encoding='utf-8'))['coverage_fail_under'])")

# ui
xvfb-run -a pytest -q tests/ui
```

## Convenciones de commits

Se recomienda usar mensajes claros y accionables. Opcionalmente, puedes usar formato **Conventional Commits**:

- `feat: ...`
- `fix: ...`
- `refactor: ...`
- `test: ...`
- `docs: ...`
- `chore: ...`

## Regla de alcance del PR

No mezclar **refactor + feature** en el mismo PR.

Si necesitas ambos, divide el trabajo:

1. PR de refactor (sin cambio de comportamiento).
2. PR de feature (sobre la base ya refactorizada).
