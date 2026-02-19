# Política de cobertura

## Baseline actual

El baseline de cobertura actual del proyecto se fija en **61%**.

Este valor refleja el estado real de la base de código a día de hoy, especialmente en áreas con mayor complejidad y superficie funcional pendiente de cubrir completamente con pruebas automatizadas, como componentes de UI y flujos de sincronización.

## Política de rampa hacia 80%

Para mejorar de forma sostenida y verificable, el umbral mínimo de cobertura seguirá esta rampa:

- **Semana/iteración 1:** 61 → 65
- **Iteración 2:** 65 → 70
- **Iteración 3:** 70 → 75
- **Iteración 4:** 75 → 80

## Reglas

- **No se bajará el umbral** de cobertura una vez incrementado.
- **Todo código nuevo debe incluir tests** y no puede reducir la cobertura global.

## Módulos prioritarios

Los esfuerzos para subir cobertura se enfocan primero en:

- `use_cases/sync_sheets.py`
- `pdf_builder`
- `sheets_client`
