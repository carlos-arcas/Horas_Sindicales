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
