# Auditoría de arranque

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
