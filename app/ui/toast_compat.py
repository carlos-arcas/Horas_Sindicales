from __future__ import annotations

import inspect
import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


def _supports_action_kwargs(method: Callable[..., object]) -> bool:
    """Detecta si un método de toast acepta action_label/action_callback.

    Nota: `ToastManager.success/error` (app/ui/widgets/toast.py) no aceptan acciones,
    pero `ToastManager.show` sí las soporta por `**opts`.
    """

    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return False

    parameters = signature.parameters.values()
    names = {parameter.name for parameter in parameters}
    if "action_label" in names and "action_callback" in names:
        return True
    return any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters)


def _safe_toast_call(
    toast: object,
    method_name: str,
    message: str,
    *,
    title: str | None = None,
    action_text: str | None = None,
    action: Callable[[], None] | None = None,
) -> bool:
    method = getattr(toast, method_name, None)
    if not callable(method):
        logger.exception("TOAST_RENDER_FAILED method=%s reason=missing_method", method_name)
        return False

    kwargs: dict[str, object] = {}
    if title is not None:
        kwargs["title"] = title

    has_action = bool(action_text and action)
    supports_actions = has_action and _supports_action_kwargs(method)
    if supports_actions:
        kwargs["action_label"] = action_text
        kwargs["action_callback"] = action

    try:
        method(message, **kwargs)
    except Exception:
        logger.exception("TOAST_RENDER_FAILED method=%s", method_name)
        return False

    if has_action and not supports_actions:
        logger.info(
            "UI_TOAST_ACTION_FALLBACK_USED method=%s action_text=%s",
            method_name,
            action_text,
        )
    return supports_actions


def ui_toast_success(
    toast: object,
    message: str,
    title: str | None = None,
    action_text: str | None = None,
    action: Callable[[], None] | None = None,
) -> bool:
    return _safe_toast_call(
        toast,
        "success",
        message,
        title=title,
        action_text=action_text,
        action=action,
    )


def ui_toast_error(
    toast: object,
    message: str,
    title: str | None = None,
    action_text: str | None = None,
    action: Callable[[], None] | None = None,
) -> bool:
    return _safe_toast_call(
        toast,
        "error",
        message,
        title=title,
        action_text=action_text,
        action=action,
    )

