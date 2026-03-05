from __future__ import annotations

from collections.abc import Iterable


def construir_info_top_level_widgets(widgets: Iterable[object]) -> list[dict[str, object]]:
    """Construye un payload serializable para logging de ventanas top-level."""
    salida: list[dict[str, object]] = []
    for widget in widgets:
        clase = widget.__class__.__name__
        salida.append(
            {
                "clase": clase,
                "object_name": _invocar_o_none(widget, "objectName"),
                "window_title": _invocar_o_none(widget, "windowTitle"),
                "is_visible": bool(_invocar_o_none(widget, "isVisible") or False),
                "is_hidden": bool(_invocar_o_none(widget, "isHidden") or False),
                "is_window": bool(_invocar_o_none(widget, "isWindow") or False),
            }
        )
    return salida


def hay_ventana_visible(toplevel_info: list[dict[str, object]]) -> bool:
    return any(bool(item.get("is_visible")) for item in toplevel_info)


def _invocar_o_none(widget: object, nombre_metodo: str):
    metodo = getattr(widget, nombre_metodo, None)
    if not callable(metodo):
        return None
    try:
        return metodo()
    except Exception:  # noqa: BLE001
        return None

