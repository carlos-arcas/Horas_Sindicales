# Política de cobertura

## Baseline actual

El baseline de cobertura actual del proyecto se fija en **63%**.

La subida registrada en este ciclo corresponde al PR **`raise-coverage-sync-normalization`**, elevando el total desde **61% → 63%** al cubrir con tests unitarios módulos de normalización y servicio de configuración de Sheets.

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
