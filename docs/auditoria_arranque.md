# Auditoría de arranque

## Wrappers builders + ajustes UI post-build

Se implementó un paquete de wrappers para cubrir métodos requeridos por los builders durante el arranque y evitar `AttributeError` en la construcción de `MainWindow`.

### Métodos cubiertos

- `_configure_time_placeholders`
- `_update_responsive_columns`
- `_normalize_input_heights`
- `_on_fecha_changed`
- `_update_solicitud_preview`
- `_on_completo_changed`
- `_on_add_pendiente`
- `_on_confirmar`

### Detalle técnico

- Se creó `app/ui/vistas/main_window/ajustes_post_build.py` con funciones idempotentes y tolerantes a widgets ausentes.
- Se añadieron mixins especializados para wrappers de post-build y handlers mínimos del formulario en:
  - `app/ui/vistas/main_window/mixins/ajustes_post_build_mixin.py`
  - `app/ui/vistas/main_window/mixins/handlers_formulario_solicitud_mixin.py`
- Se integraron los mixins en `MainWindow` pública (`main_window_vista.py`) sin mover lógica de negocio a la vista.
- Se agregaron tests de no-crash con doubles de ventana para validar comportamiento mínimo sin runtime Qt completo.
=======
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
