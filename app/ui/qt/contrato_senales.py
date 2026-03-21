from __future__ import annotations

from dataclasses import dataclass
import inspect
from typing import Any, Callable


@dataclass(frozen=True)
class ContratoSenal:
    emisor: str
    senal: str
    handler: str
    adaptador: str
    critico: bool = True


@dataclass(frozen=True)
class IncidenciaContratoSenal:
    emisor: str
    senal: str
    handler: str
    motivo: str


_SENAL_SELECTION_MODEL = "selectionModel"
_SENAL_SELECTION_CHANGED = "selectionChanged"


CONTRATOS_SENALES_MAIN_WINDOW: tuple[ContratoSenal, ...] = (
    ContratoSenal("persona_combo", "currentIndexChanged", "_on_persona_changed", "adaptar_index"),
    ContratoSenal("config_delegada_combo", "currentIndexChanged", "_on_config_delegada_changed", "adaptar_index"),
    ContratoSenal("historico_delegada_combo", "currentIndexChanged", "_on_historico_filter_changed", "adaptar_index"),
    ContratoSenal("pendientes_table", f"{_SENAL_SELECTION_MODEL}.{_SENAL_SELECTION_CHANGED}", "_on_pending_selection_changed", "adaptar_selection_changed"),
    ContratoSenal("huerfanas_table", f"{_SENAL_SELECTION_MODEL}.{_SENAL_SELECTION_CHANGED}", "_on_pending_selection_changed", "adaptar_selection_changed"),
    ContratoSenal("historico_table", f"{_SENAL_SELECTION_MODEL}.{_SENAL_SELECTION_CHANGED}", "_on_historico_selection_changed", "adaptar_selection_changed"),
    ContratoSenal("completo_check", "toggled", "_on_completo_changed", "adaptar_bool"),
    ContratoSenal("fecha_input", "dateChanged", "_on_fecha_changed", "adaptar_qdate"),
    ContratoSenal("desde_input", "timeChanged", "_on_desde_changed", "adaptar_qtime"),
    ContratoSenal("hasta_input", "timeChanged", "_on_hasta_changed", "adaptar_qtime"),
    ContratoSenal("notas_input", "textChanged", "_update_solicitud_preview", "adaptar_sin_args"),
    ContratoSenal("main_tabs", "currentChanged", "_on_main_tab_changed", "adaptar_index"),
    ContratoSenal("historico_search_input", "textChanged", "_on_historico_search_text_changed", "adaptar_texto"),
)


def validar_contrato_senales(
    emisores_disponibles: set[str],
    handlers_disponibles: set[str],
    adaptadores_disponibles: set[str],
) -> list[IncidenciaContratoSenal]:
    incidencias: list[IncidenciaContratoSenal] = []
    contratos_vistos: set[tuple[str, str]] = set()
    for contrato in CONTRATOS_SENALES_MAIN_WINDOW:
        if not contrato.emisor.strip() or not contrato.senal.strip() or not contrato.handler.strip() or not contrato.adaptador.strip():
            incidencias.append(
                IncidenciaContratoSenal(
                    emisor=contrato.emisor,
                    senal=contrato.senal,
                    handler=contrato.handler,
                    motivo="CONTRATO_SENAL_INCONSISTENTE",
                )
            )
            continue

        clave = (contrato.emisor, contrato.senal)
        if clave in contratos_vistos:
            incidencias.append(
                IncidenciaContratoSenal(
                    emisor=contrato.emisor,
                    senal=contrato.senal,
                    handler=contrato.handler,
                    motivo="CONTRATO_SENAL_DUPLICADO",
                )
            )
            continue
        contratos_vistos.add(clave)

        if contrato.emisor not in emisores_disponibles:
            incidencias.append(
                IncidenciaContratoSenal(
                    emisor=contrato.emisor,
                    senal=contrato.senal,
                    handler=contrato.handler,
                    motivo="EMISOR_NO_EXISTENTE",
                )
            )
        if contrato.handler not in handlers_disponibles:
            incidencias.append(
                IncidenciaContratoSenal(
                    emisor=contrato.emisor,
                    senal=contrato.senal,
                    handler=contrato.handler,
                    motivo="HANDLER_NO_EXISTENTE",
                )
            )
        if contrato.adaptador not in adaptadores_disponibles:
            incidencias.append(
                IncidenciaContratoSenal(
                    emisor=contrato.emisor,
                    senal=contrato.senal,
                    handler=contrato.handler,
                    motivo="ADAPTADOR_NO_EXISTENTE",
                )
            )
    return incidencias


def _resolver_argumentos_invocacion(
    fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> tuple[tuple[Any, ...], dict[str, Any]] | None:
    try:
        firma = inspect.signature(fn)
    except (TypeError, ValueError):
        return None

    parametros = tuple(firma.parameters.values())
    acepta_varargs = any(param.kind == inspect.Parameter.VAR_POSITIONAL for param in parametros)
    acepta_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parametros)
    nombres_kwargs_validos = {
        param.name
        for param in parametros
        if param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    kwargs_ajustados = kwargs if acepta_kwargs else {nombre: valor for nombre, valor in kwargs.items() if nombre in nombres_kwargs_validos}

    candidatos_args: tuple[tuple[Any, ...], ...]
    if acepta_varargs:
        candidatos_args = (args,)
    else:
        max_args = sum(
            1
            for param in parametros
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        limite_superior = min(len(args), max_args)
        candidatos_args = tuple(args[:cantidad] for cantidad in range(limite_superior, -1, -1))

    for args_candidatos in candidatos_args:
        try:
            firma.bind(*args_candidatos, **kwargs_ajustados)
        except TypeError:
            continue
        return args_candidatos, kwargs_ajustados

    return None


def _invocar_tolerante(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    invocacion = _resolver_argumentos_invocacion(fn, *args, **kwargs)
    if invocacion is None:
        return fn(*args, **kwargs)

    args_ajustados, kwargs_ajustados = invocacion
    return fn(*args_ajustados, **kwargs_ajustados)


def _normalizar_bool(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        return valor != 0
    if isinstance(valor, str):
        return valor.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}
    return bool(valor)


def adaptar_sin_args(fn: Callable[..., Any]) -> Callable[..., Any]:
    def _slot(*_args: Any, **_kwargs: Any) -> Any:
        return _invocar_tolerante(fn)

    return _slot



def adaptar_bool(fn: Callable[..., Any]) -> Callable[..., Any]:
    def _slot(*args: Any, **_kwargs: Any) -> Any:
        valor = _normalizar_bool(args[0]) if args else False
        return _invocar_tolerante(fn, valor)

    return _slot



def adaptar_index(fn: Callable[..., Any]) -> Callable[..., Any]:
    def _slot(*args: Any, **_kwargs: Any) -> Any:
        if not args:
            return _invocar_tolerante(fn, -1)
        try:
            return _invocar_tolerante(fn, int(args[0]))
        except (TypeError, ValueError):
            return _invocar_tolerante(fn, -1)

    return _slot



def adaptar_texto(fn: Callable[..., Any]) -> Callable[..., Any]:
    def _slot(*args: Any, **_kwargs: Any) -> Any:
        texto = "" if not args else str(args[0])
        return _invocar_tolerante(fn, texto)

    return _slot



def adaptar_selection_changed(fn: Callable[..., Any]) -> Callable[..., Any]:
    def _slot(*args: Any, **_kwargs: Any) -> Any:
        actual = args[0] if len(args) >= 1 else None
        anterior = args[1] if len(args) >= 2 else None
        return _invocar_tolerante(fn, actual, anterior)

    return _slot



def adaptar_qdate(fn: Callable[..., Any]) -> Callable[..., Any]:
    def _slot(*args: Any, **_kwargs: Any) -> Any:
        fecha = args[0] if args else None
        return _invocar_tolerante(fn, fecha)

    return _slot



def adaptar_qtime(fn: Callable[..., Any]) -> Callable[..., Any]:
    def _slot(*args: Any, **_kwargs: Any) -> Any:
        tiempo = args[0] if args else None
        return _invocar_tolerante(fn, tiempo)

    return _slot



def adaptar_variable(fn: Callable[..., Any]) -> Callable[..., Any]:
    def _slot(*args: Any, **kwargs: Any) -> Any:
        return _invocar_tolerante(fn, *args, **kwargs)

    return _slot


ADAPTADORES_SENALES: dict[str, Callable[[Callable[..., Any]], Callable[..., Any]]] = {
    "adaptar_sin_args": adaptar_sin_args,
    "adaptar_bool": adaptar_bool,
    "adaptar_index": adaptar_index,
    "adaptar_texto": adaptar_texto,
    "adaptar_selection_changed": adaptar_selection_changed,
    "adaptar_qdate": adaptar_qdate,
    "adaptar_qtime": adaptar_qtime,
    "adaptar_variable": adaptar_variable,
}
