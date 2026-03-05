from __future__ import annotations

from typing import Any


def cerrar_toast(widget: Any, toast_id: str) -> None:
    signal = getattr(widget, "cerrado", None)
    if signal is not None and hasattr(signal, "emit"):
        signal.emit(toast_id)
    hide_method = getattr(widget, "hide", None)
    if callable(hide_method):
        hide_method()
    delete_later = getattr(widget, "deleteLater", None)
    if callable(delete_later):
        delete_later()


__all__ = [cerrar_toast.__name__]
