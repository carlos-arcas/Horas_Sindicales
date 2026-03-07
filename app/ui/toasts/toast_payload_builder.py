from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from time import monotonic
from typing import Callable

from app.ui.copy_catalog import copy_text


@dataclass(frozen=True, slots=True)
class ToastPayloadEntrada:
    message: str | None
    level: str
    title: str | None
    action_label: str | None
    action_callback: Callable[[], None] | None
    details: str | None
    correlation_id: str | None
    code: str | None
    origin: str | None
    exc_info: BaseException | tuple[type[BaseException], BaseException, object] | bool | None
    duration_ms: int | None
    opts: dict[str, object]


@dataclass(frozen=True, slots=True)
class ToastPayloadResuelto:
    toast_id: str
    titulo: str
    mensaje: str
    nivel: str
    detalles: str | None
    codigo: str
    correlacion_id: str | None
    origen: str
    action_label: str | None
    action_callback: Callable[[], None] | None
    dedupe_key: str
    duracion_ms: int


def resolver_campo_texto(valor: str | None, opts: dict[str, object], *claves: str) -> str | None:
    if isinstance(valor, str):
        return valor
    for clave in claves:
        extra = opts.get(clave)
        if isinstance(extra, str):
            return extra
    return None


def resolver_detalles(
    detalles: str | None,
    exc_info: BaseException | tuple[type[BaseException], BaseException, object] | bool | None,
) -> tuple[str | None, str | None]:
    if isinstance(exc_info, tuple) and exc_info and isinstance(exc_info[0], type):
        return "".join(traceback.format_exception(*exc_info)), exc_info[0].__name__
    if isinstance(exc_info, BaseException):
        return "".join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__)), type(exc_info).__name__
    if exc_info is True:
        clase, valor, tb = sys.exc_info()
        if clase is not None and valor is not None:
            return "".join(traceback.format_exception(clase, valor, tb)), clase.__name__
    return detalles, None


def crear_dedupe_key(codigo: str, origen: str, tipo_excepcion: str | None) -> str:
    return f"{codigo}:{origen}:{tipo_excepcion or 'sin_excepcion'}"


def construir_toast_payload(entrada: ToastPayloadEntrada) -> ToastPayloadResuelto | None:
    if entrada.message is None:
        return None
    details_value = resolver_campo_texto(entrada.details, entrada.opts, "details")
    code_value = resolver_campo_texto(entrada.code, entrada.opts, "code", "codigo") or "SIN_CODIGO"
    origin_value = resolver_campo_texto(entrada.origin, entrada.opts, "origin", "origen") or "origen_desconocido"
    correlation_value = resolver_campo_texto(entrada.correlation_id, entrada.opts, "correlation_id", "correlacion_id")
    detalles_completos, tipo_excepcion = resolver_detalles(details_value, entrada.exc_info)
    dedupe_key = crear_dedupe_key(code_value, origin_value, tipo_excepcion)
    return ToastPayloadResuelto(
        toast_id=f"{dedupe_key}:{int(monotonic() * 1000)}",
        titulo=entrada.title or copy_text("ui.toast.notificacion"),
        mensaje=entrada.message,
        nivel=entrada.level,
        detalles=detalles_completos,
        codigo=code_value,
        correlacion_id=correlation_value,
        origen=origin_value,
        action_label=entrada.action_label if isinstance(entrada.action_label, str) else None,
        action_callback=entrada.action_callback,
        dedupe_key=dedupe_key,
        duracion_ms=8000 if entrada.duration_ms is None else max(0, int(entrada.duration_ms)),
    )


__all__ = [
    ToastPayloadEntrada.__name__,
    ToastPayloadResuelto.__name__,
    resolver_campo_texto.__name__,
    resolver_detalles.__name__,
    crear_dedupe_key.__name__,
    construir_toast_payload.__name__,
]
