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
3. (Opcional) Ejecutar `python scripts/quality_gate.py`.
