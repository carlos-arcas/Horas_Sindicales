# Política TZ en `sync_reporting`

Fecha: 2026-03-02

## Decisión

Para parsear timestamps ISO en reportes de sincronización (`app/ui/sync_reporting.py`):

- Si el ISO es **aware**, se convierte a UTC.
- Si el ISO es **naive** (sin `tzinfo`), se asume **zona horaria local del sistema** y luego se convierte a UTC.
- Si el ISO es inválido, no se rompe la UI: la duración se degrada a `0` y se registra un warning estructurado.

## Motivación

Evitar que datos corruptos o incompletos (`generated_at`, `now`) provoquen excepciones en la UI al construir reportes de sincronización.

## Observabilidad

Se registran eventos estructurados:

- `sync_report_iso_invalido`
- `sync_report_tz_naive_normalizado`
- `sync_report_duracion_iso_invalido`

Los payloads incluyen solo campos mínimos para diagnóstico (`generated_at`, `now`, `valor_iso`, `tz_local`) y evitan volcar objetos grandes como el plan completo.

## Verificación

1. Ejecutar `pytest tests/application/test_sync_reporting_datetime.py`.
2. Confirmar que:
   - ISO inválido no rompe la generación de reporte y devuelve `duration_ms = 0`.
   - ISO naive genera log de normalización de TZ local.
