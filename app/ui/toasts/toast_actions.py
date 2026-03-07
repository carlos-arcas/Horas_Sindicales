from __future__ import annotations

from typing import Any


def cerrar_toast(widget: Any, toast_id: str) -> None:
    signal = getattr(widget, "cerrado", None)
    if signal is not None and hasattr(signal, "emit"):
        signal.emit(toast_id)
        return
    close_method = getattr(widget, "close", None)
    if callable(close_method):
        close_method()
        return
    hide_method = getattr(widget, "hide", None)
    if callable(hide_method):
        hide_method()


__all__ = [cerrar_toast.__name__]
