from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)


def toast_success(
    toast: object,
    message: str,
    title: str | None = None,
    *,
    action_label: str | None = None,
    action_callback: Callable[[], None] | None = None,
) -> None:
    try:
        try:
            kwargs: dict[str, object] = {}
            if title:
                kwargs["title"] = title
            if action_label is not None and action_callback is not None:
                kwargs["action_label"] = action_label
                kwargs["action_callback"] = action_callback

            if kwargs:
                toast.success(message, **kwargs)
            else:
                toast.success(message)
        except TypeError:
            toast.success(message)
    except Exception:
        logger.exception("UI_TOAST_FAILED success")


def toast_error(
    toast: object,
    message: str,
    title: str | None = None,
    *,
    action_label: str | None = None,
    action_callback: Callable[[], None] | None = None,
) -> None:
    try:
        try:
            kwargs: dict[str, object] = {}
            if title:
                kwargs["title"] = title
            if action_label is not None and action_callback is not None:
                kwargs["action_label"] = action_label
                kwargs["action_callback"] = action_callback

            if kwargs:
                toast.error(message, **kwargs)
            else:
                toast.error(message)
        except TypeError:
            toast.error(message)
    except Exception:
        logger.exception("UI_TOAST_FAILED error")
