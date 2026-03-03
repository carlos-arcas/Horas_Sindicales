from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.ui.copy_catalog import copy_text

_REASON_CODE_SLOT_EXCEPTION = "QT_SLOT_EXCEPTION"


def _notificar_error_toast(toast: Any, *, contexto: str) -> None:
    metodo_error = getattr(toast, "error", None)
    if not callable(metodo_error):
        return
    metodo_error(copy_text("ui.wiring.slot_error"))


def envolver_slot_seguro(
    fn: Callable[..., Any],
    *,
    contexto: str,
    logger: Any,
    toast: Any = None,
) -> Callable[..., None]:
    def _slot_seguro(*args: Any, **kwargs: Any) -> None:
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception(
                "qt_slot_exception",
                extra={
                    "reason_code": _REASON_CODE_SLOT_EXCEPTION,
                    "contexto": contexto,
                    "handler_name": getattr(fn, "__name__", repr(fn)),
                },
            )
            if toast is not None:
                try:
                    _notificar_error_toast(toast, contexto=contexto)
                except Exception:
                    logger.exception(
                        "qt_slot_toast_exception",
                        extra={
                            "reason_code": _REASON_CODE_SLOT_EXCEPTION,
                            "contexto": contexto,
                            "handler_name": getattr(fn, "__name__", repr(fn)),
                        },
                    )

    return _slot_seguro
