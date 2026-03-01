# Auditoría de arranque

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
