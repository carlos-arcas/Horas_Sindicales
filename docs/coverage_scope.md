# Alcance de cobertura en CI

La cobertura mínima de CI (>=63%) se evalúa sobre `app/domain/**` y `app/application/**`, porque ahí vive la lógica de negocio y reglas operativas.

## Exclusiones intencionales

- `app/ui/**` (incluye `app/ui/vistas/main_window_vista.py`):
  - La UI declarativa depende de Qt/event-loop y suele ser más frágil (flaky) en CI.
  - Su cobertura de líneas no refleja con fidelidad el valor funcional del dominio.
- `app/entrypoints/**`:
  - Son wiring/arranque de proceso y se validan mejor con smoke tests de integración, no con unit tests de cobertura fina.

## Criterio

No se usa esta exclusión para "maquillar" el resultado: se mantiene y prioriza la cobertura donde se toman decisiones de negocio (`domain`/`application`).
