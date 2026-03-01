from __future__ import annotations

from typing import Any


def es_objeto_qt_valido(obj: Any) -> bool:
    if obj is None:
        return False
    try:
        from shiboken6 import isValid as shiboken_is_valid
    except Exception:
        shiboken_is_valid = None

    if shiboken_is_valid is not None:
        try:
            return bool(shiboken_is_valid(obj))
        except RuntimeError:
            return False

    try:
        bool(obj)
        return True
    except RuntimeError:
        return False


def safe_hide(widget: Any) -> None:
    if not es_objeto_qt_valido(widget):
        return
    try:
        if hasattr(widget, "request_close"):
            widget.request_close()
            return
        if hasattr(widget, "hide"):
            widget.hide()
        if hasattr(widget, "close"):
            widget.close()
    except RuntimeError:
        return


def safe_quit_thread(thread: Any) -> None:
    if not es_objeto_qt_valido(thread):
        return
    if not hasattr(thread, "quit"):
        return
    try:
        if hasattr(thread, "isRunning") and not thread.isRunning():
            return
    except RuntimeError:
        return
    try:
        thread.quit()
    except RuntimeError:
        return
