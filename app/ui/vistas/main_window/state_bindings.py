from __future__ import annotations

import inspect
import logging
from functools import lru_cache
from typing import Any, Callable


logger = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def _obtener_firma(fn: Callable[..., Any]) -> inspect.Signature | None:
    try:
        return inspect.signature(fn)
    except (TypeError, ValueError):
        return None


def _hay_mismatch_de_aridad(
    fn: Callable[..., Any], self_obj: Any, args: tuple[Any, ...], kwargs: dict[str, Any], error: TypeError
) -> bool:
    firma = _obtener_firma(fn)
    if firma is None:
        return False
    try:
        firma.bind(self_obj, *args, **kwargs)
    except TypeError:
        return True
    return False


def _max_args_posicionales_para_senal(fn: Callable[..., Any]) -> int | None:
    firma = _obtener_firma(fn)
    if firma is None:
        return 0

    params = tuple(firma.parameters.values())
    if any(param.kind == inspect.Parameter.VAR_POSITIONAL for param in params):
        return None

    posicionales = [
        param
        for param in params
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    return max(len(posicionales) - 1, 0)


def _log_arity_fallback(fn: Callable[..., Any], args: tuple[Any, ...], args_compatibles: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    if args_compatibles == args and not kwargs:
        return
    logger.warning(
        "UI_BINDING_ARITY_FALLBACK",
        extra={
            "extra": {
                "reason_code": "UI_BINDING_ARITY_FALLBACK",
                "handler": getattr(fn, "__name__", repr(fn)),
                "args_recibidos": len(args),
                "args_utilizados": len(args_compatibles),
                "kwargs_descartados": tuple(kwargs.keys()),
            }
        },
    )


def _recortar_args_por_firma(fn: Callable[..., Any], self_obj: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    max_args_senal = _max_args_posicionales_para_senal(fn)
    args_compatibles = args if max_args_senal is None else args[:max_args_senal]
    _log_arity_fallback(fn, args, args_compatibles, kwargs)
    return fn(self_obj, *args_compatibles)


def _invocar_handler_compatible(fn: Callable[..., Any], self_obj: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    try:
        return fn(self_obj, *args, **kwargs)
    except TypeError as error:
        if not _hay_mismatch_de_aridad(fn, self_obj, args, kwargs, error):
            raise
        return _recortar_args_por_firma(fn, self_obj, args, kwargs)


def _adaptar_slot_a_senal(fn: Callable[..., Any]) -> Callable[..., Any]:
    def _slot_compatible(self: Any, *args: Any, **kwargs: Any) -> Any:
        return _invocar_handler_compatible(fn, self, args, kwargs)

    return _slot_compatible


def _bind_handler(clase: type, nombre_metodo: str, fn: Callable[..., Any]) -> None:
    setattr(clase, nombre_metodo, _adaptar_slot_a_senal(fn))


def registrar_state_bindings(clase: type) -> None:
    from app.ui.vistas import historico_actions

    bindings: dict[str, Callable[..., Any]] = {
        "_apply_historico_filters": historico_actions.apply_historico_filters,
        "_apply_historico_default_range": historico_actions.apply_historico_default_range,
        "_apply_historico_last_30_days": historico_actions.apply_historico_last_30_days,
        "_on_historico_periodo_mode_changed": historico_actions.on_historico_periodo_mode_changed,
        "_on_historico_apply_filters": historico_actions.on_historico_apply_filters,
        "_configure_historico_focus_order": historico_actions.configure_historico_focus_order,
        "_focus_historico_search": historico_actions.focus_historico_search,
        "_selected_historico_solicitudes": historico_actions.selected_historico_solicitudes,
        "_selected_historico": historico_actions.selected_historico,
        "_sync_historico_select_all_visible_state": historico_actions.sync_historico_select_all_visible_state,
        "_on_export_historico_pdf": historico_actions.on_export_historico_pdf,
    }
    for nombre_metodo, fn in bindings.items():
        _bind_handler(clase, nombre_metodo, fn)
