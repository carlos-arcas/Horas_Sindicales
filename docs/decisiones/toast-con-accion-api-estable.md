# Toast con acción: API estable

## Decisión
Se estabiliza la API de `ToastManager/GestorToasts` para aceptar en `success(...)` y `error(...)` los parámetros:

- `action_label: str | None = None`
- `action_callback: Callable[[], None] | None = None`

Además, se mantiene compatibilidad con aliases históricos (`action_text`, `action`) y se encapsula la resolución en el modelo `AccionToast`.

## Motivo
Evitar `TypeError` en integraciones que envían acciones opcionales, incluso cuando la implementación concreta de `show(...)` no soporte esos kwargs.

## Verificación rápida
1. Ejecutar `ruff check .`.
2. Ejecutar `pytest -q`.
3. (Opcional) Ejecutar `python -m scripts.quality_gate`.

## Actualización: guardrail para callback de acción (2026-03)
Se incorpora el helper `app/ui/toasts/ejecutar_callback_seguro.py` para ejecutar `action_callback` con tolerancia a fallos. La `TarjetaToast` ahora delega en este helper para evitar excepciones no controladas en el event loop de Qt.

### Detalles
- `ejecutar_callback_seguro(...)` encapsula `try/except`, registra `toast_action_callback_failed` con `contexto` y `correlation_id`, y nunca relanza al loop de UI.
- El `contexto` se normaliza para no exponer rutas completas innecesarias en logs (se conservan sólo los últimos segmentos para depuración).

### Verificación rápida
1. Ejecutar `pytest -q tests/test_ejecutar_callback_seguro.py`.
2. Ejecutar `ruff check app/ui/toasts/ejecutar_callback_seguro.py app/ui/widgets/widget_toast.py tests/test_ejecutar_callback_seguro.py`.
## Actualización (tests puros sin Qt)
Se agregan pruebas unitarias en `tests/ui/test_toast_manager_action_kwargs_puros.py` que cargan `app.ui.widgets.toast` con stubs para evitar runtime de Qt y blindan que `success/error` aceptan `action_label/action_callback` sin `TypeError`.
Además, se valida por firma (`inspect.signature`) que ambos parámetros opcionales permanezcan expuestos y que un `action_callback` no callable se degrade a `None` de forma segura.
