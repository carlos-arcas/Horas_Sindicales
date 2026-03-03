from __future__ import annotations

from typing import Any


def cerrar_toast_desde_ui(widget: Any, toast_id: str) -> None:
    signal = getattr(widget, "cerrado", None)
    if signal is not None and hasattr(signal, "emit"):
        signal.emit(toast_id)
    close_method = getattr(widget, "close", None)
    if callable(close_method):
        close_method()


__all__ = [cerrar_toast_desde_ui.__name__]
