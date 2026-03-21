from __future__ import annotations

import inspect
from typing import Any, Callable



def _is_type_error_por_firma(error: TypeError) -> bool:
    mensaje = str(error)
    patrones = (
        "positional argument",
        "required positional argument",
        "got multiple values for argument",
    )
    return any(patron in mensaje for patron in patrones)


def _recortar_args_por_firma(fn: Callable[..., Any], self_obj: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return fn(self_obj)

    params = tuple(signature.parameters.values())
    acepta_varargs = any(param.kind == inspect.Parameter.VAR_POSITIONAL for param in params)
    if acepta_varargs:
        return fn(self_obj, *args, **kwargs)

    posicionales = [
        p
        for p in params
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    max_args_senal = max(len(posicionales) - 1, 0)
    return fn(self_obj, *args[:max_args_senal], **kwargs)


def _invocar_handler_compatible(fn: Callable[..., Any], self_obj: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    try:
        return fn(self_obj, *args, **kwargs)
    except TypeError as error:
        if not _is_type_error_por_firma(error):
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
    from app.ui.vistas.main_window import state_historico

    bindings: dict[str, Callable[..., Any]] = {
        "_apply_historico_filters": historico_actions.apply_historico_filters,
        "_apply_historico_default_range": historico_actions.apply_historico_default_range,
        "_apply_historico_last_30_days": historico_actions.apply_historico_last_30_days,
        "_on_historico_periodo_mode_changed": historico_actions.on_historico_periodo_mode_changed,
        "_on_historico_apply_filters": historico_actions.on_historico_apply_filters,
        "_on_historico_filter_changed": historico_actions.on_historico_filter_changed,
        "_on_historico_search_text_changed": historico_actions.on_historico_search_text_changed,
        "_construir_filtro_historico": historico_actions.build_historico_filters,
        "_configure_historico_focus_order": historico_actions.configure_historico_focus_order,
        "_focus_historico_search": historico_actions.focus_historico_search,
        "_selected_historico_solicitudes": state_historico.obtener_solicitudes_historico_seleccionadas,
        "_selected_historico": state_historico.obtener_solicitud_historico_seleccionada,
        "_sync_historico_select_all_visible_state": historico_actions.sync_historico_select_all_visible_state,
        "_on_export_historico_pdf": historico_actions.on_export_historico_pdf,
    }
    for nombre_metodo, fn in bindings.items():
        _bind_handler(clase, nombre_metodo, fn)
