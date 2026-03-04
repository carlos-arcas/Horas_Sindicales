# Roadmap Senior

## 2026-03-04 — Coverage CORE
- Coverage CORE (estimación local con `trace`): **antes ~88% -> después ~89%** en `app/domain` + `app/application`.
- Tests añadidos:
  - `tests/domain/test_time_utils_cobertura.py` para ramas de validación y normalización de `time_utils`.
  - `tests/application/test_personas_use_case_cobertura.py` para ramas de orquestación de `PersonaUseCases`.
- Objetivo: subir margen sobre el umbral de CI (`>=85%`) sin cambios funcionales.

## 2026-03-04 — Coverage CORE (bloqueo entorno pytest-cov)
- Coverage CORE: **antes N/D -> después N/D** (no medible en este entorno).
- Tests añadidos: **ninguno**; ciclo detenido por falta de `pytest-cov` (comando canónico falla al parsear `--cov`).
- Objetivo de auditoría: dejar evidencia explícita del bloqueo para destrabar CI reproduciendo el prerequisito de cobertura en entorno con dependencias de dev.

