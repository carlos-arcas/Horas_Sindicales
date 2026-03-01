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
=======
## Thread-safety + cleanup idempotente

### Before
- El cierre del splash y del `QThread` se hacía con llamadas directas (`hide/close/quit`) en distintos puntos.
- En escenarios de fallo temprano, el cleanup volvía a invocar métodos sobre objetos Qt ya destruidos.
- Aunque las señales se conectaban en `QueuedConnection`, no se forzaba de forma explícita el tramo de UI en `on_finished/on_failed`.

### After
- Se creó `app/ui/qt_safe_ops.py` con operaciones idempotentes:
  - `es_objeto_qt_valido`.
  - `safe_hide` para `SplashWindow`/widgets.
  - `safe_quit_thread` para `QThread`.
- `ui_main` y `coordinador_arranque` usan estas operaciones seguras para cleanup.
- `on_finished` y `on_failed` despachan la parte de UI con `QTimer.singleShot(0, ...)` para garantizar ejecución en el hilo principal.
- Ante excepción en arranque se conserva `incident_id`, logging operacional y cierre seguro de splash/thread sin `RuntimeError` en cleanup.

### Evidencia de validación
- Unit tests nuevos para `qt_safe_ops` con fakes sin Qt.
- Smoke/UI tests existentes ajustados para validar ruta de ejecución diferida en `singleShot`.
- 
## Toast API compat

### Before
- El facade `ToastManager.success()` y `ToastManager.error()` podía romper con `TypeError` cuando se invocaba con `action_label`/`action_callback` desde capas que esperaban la API histórica.
- El código aceptaba `**opts` sin validación estricta, lo que podía ocultar errores de integración y propagar kwargs no soportados.

### After
- `success()` y `error()` mantienen compatibilidad retro y aceptan `action_label`/`action_callback` sin requerir cambios en call-sites.
- Se agregó mapeo explícito de aliases: `action_text -> action_label` y `action -> action_callback`.
- Si `action_callback` es `None`, no se agrega acción y no hay crash.
- Cualquier kwarg desconocido ahora se rechaza con `ValueError` y registro de error estructurado.

### Impacto
- Se elimina el crash de arranque relacionado con toasts con acción.
- Se mejora la trazabilidad de errores de integración por validación explícita de kwargs.
- Se reduce deuda técnica al evitar tolerancia silenciosa de parámetros inválidos.
