# Decisión técnica: política TZ para ISO naive en reportes de sincronización

## Contexto
En reportes de sincronización pueden recibirse timestamps ISO sin zona horaria (`naive`).
Si se comparan contra timestamps aware sin normalización, Python lanza errores y la UI puede romperse.

## Decisión
- Se adopta política explícita: **todo ISO naive se interpreta en zona horaria local del sistema**.
- En normalización de zona se registra evento estructurado `normalizacion_tz_naive_local`.
- Si un ISO es inválido, se registra evento estructurado `iso_datetime_invalido`.
- En simulación de sincronización, ante `generated_at` inválido se registra `sync_simulacion_iso_invalido` con campos mínimos `generated_at` y `now`, y se usa duración `0` para evitar caída de UI.

## Verificación
1. Ejecutar tests de parsing y reporte:
   - `pytest tests/application/test_parseo_iso_datetime.py tests/application/test_sync_reporting_datetime.py`
2. Revisar que existen logs estructurados para:
   - `iso_datetime_invalido`
   - `normalizacion_tz_naive_local`
   - `sync_simulacion_iso_invalido`
