from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def toast_success(toast: object, message: str, title: str | None = None) -> None:
    try:
        try:
            if title:
                toast.success(message, title=title)
            else:
                toast.success(message)
        except TypeError:
            toast.success(message)
    except Exception:
        logger.exception("UI_TOAST_FAILED success")


def toast_error(toast: object, message: str, title: str | None = None) -> None:
    try:
        try:
            if title:
                toast.error(message, title=title)
            else:
                toast.error(message)
        except TypeError:
            toast.error(message)
    except Exception:
        logger.exception("UI_TOAST_FAILED error")
