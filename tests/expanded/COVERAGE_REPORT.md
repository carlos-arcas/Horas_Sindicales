# Coverage report (local run)

## Before
- Referencia inicial solicitada en el prompt: **~61%**.

## After
- En este entorno no fue posible ejecutar `pytest --cov ...` porque falta `pytest-cov` y la red bloquea su instalación.
- Validación funcional ejecutada: `PYTHONPATH=. pytest -q` → **195 passed, 1 skipped**.

## Nota
- Se añadieron tests de alto impacto en application/domain/infrastructure para aumentar cobertura real de reglas de negocio y ramas de error.
