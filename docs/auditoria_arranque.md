# Auditoría de arranque

## Datetime normalization sync_reporting

### Before
- `app/ui/sync_reporting.py` calculaba duraciones con restas directas entre `datetime` parseados desde ISO.
- Cuando un valor venía `naive` y el otro `aware`, Python lanzaba: `TypeError: can't subtract offset-naive and offset-aware datetimes`.

### After
- Se agregó `app/application/tiempo/normalizacion_datetime.py` con utilidades puras de `datetime`:
  - `parsear_iso_datetime(texto, tz_por_defecto)` para obtener siempre `datetime` aware.
  - `duracion_ms(inicio, fin)` para calcular duración segura (`int >= 0`) sin fallos naive/aware.
- `app/ui/sync_reporting.py` usa ahora el helper para todo cálculo de `duration_ms`.
- Se añadieron pruebas de regresión en `tests/ui/test_sync_reporting_datetime_normalization.py` cubriendo ambos escenarios mixtos (now naive + plan aware, y viceversa).
