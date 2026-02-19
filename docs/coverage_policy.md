# Política de cobertura

## Baseline actual

El baseline de cobertura actual del proyecto se fija en **63%**.

La subida registrada en este ciclo corresponde al PR **`raise-coverage-sync-normalization`**, elevando el total desde **61% → 63%** al cubrir con tests unitarios módulos de normalización y servicio de configuración de Sheets.

## Estado del ciclo `raise-coverage-sync-sheets-use-case`

En este ciclo se añadieron tests de escenarios para `app/application/sync_sheets_use_case.py`.

> Nota: en este entorno local no está disponible `pytest-cov`, por lo que la medición de porcentaje total y del módulo se valida en CI.

Regla aplicada para este PR:

- Si CI reporta subida del total, actualizar `--cov-fail-under` al nuevo baseline redondeado hacia abajo en el mismo PR.
- Si CI no reporta subida, mantener baseline y umbral vigentes.

## Política de rampa hacia 80%

Para mejorar de forma sostenida y verificable, el umbral mínimo de cobertura seguirá esta rampa:

- **Iteración actual:** 63 → 66
- **Iteración 2:** 66 → 70
- **Iteración 3:** 70 → 75
- **Iteración 4:** 75 → 80

## Reglas

- **No se bajará el umbral** de cobertura una vez incrementado.
- **Todo código nuevo debe incluir tests** y no puede reducir la cobertura global.

## Módulos prioritarios

Los esfuerzos para subir cobertura se enfocan primero en:

- `app/application/sync.py`
- `app/infrastructure/sheets_client.py`
- `app/application/use_cases/sync_sheets.py`
