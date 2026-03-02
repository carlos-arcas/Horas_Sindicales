from __future__ import annotations

import logging
import os
from inspect import Parameter, signature

from app.ui.qt_hilos import es_hilo_ui

logger = logging.getLogger(__name__)

_REASON_CODE_HANDLER_FALTANTE = "WIRING_HANDLER_MISSING"
_REASON_CODE_FIRMA_INVALIDA = "WIRING_HANDLER_INVALID_SIGNATURE"
_REASON_CODE_HILO_INVALIDO = "WIRING_UI_THREAD_REQUIRED"
_ATTR_BINDINGS = "_wiring_bindings_registrados"


def _env_habilitado(nombre: str) -> bool:
    valor = os.getenv(nombre, "")
    return valor.strip().lower() in {"1", "true", "yes", "on"}


def _modo_estricto() -> bool:
    return _env_habilitado("CI") or _env_habilitado("WIRING_STRICT")


def _binding_ya_registrado(window, key: tuple[int, str, str]) -> bool:
    registrados = getattr(window, _ATTR_BINDINGS, None)
    if registrados is None:
        registrados = set()
        setattr(window, _ATTR_BINDINGS, registrados)
    if key in registrados:
        return True
    registrados.add(key)
    return False


def _acepta_argumento(handler) -> bool:
    try:
        parametros = signature(handler).parameters.values()
    except (TypeError, ValueError):
        return True

    for parametro in parametros:
        if parametro.kind in {
            Parameter.POSITIONAL_ONLY,
            Parameter.POSITIONAL_OR_KEYWORD,
            Parameter.VAR_POSITIONAL,
        }:
            return True
    return False


def _asegurar_hilo_gui(*, contexto: str, handler_name: str, window, signal) -> None:
    if es_hilo_ui():
        return
    mensaje = "Operacion de wiring UI fuera del hilo GUI."
    logger.error(
        mensaje,
        extra={
            "reason_code": _REASON_CODE_HILO_INVALIDO,
            "contexto": contexto,
            "handler_name": handler_name,
            "widget": type(window).__name__,
            "signal": type(signal).__name__,
        },
    )
    raise RuntimeError(f"{mensaje} contexto={contexto}")


def conectar_signal(
    window, signal, handler_name: str, *, contexto: str, signal_pasa_args: bool = False
) -> None:
    _asegurar_hilo_gui(
        contexto=contexto, handler_name=handler_name, window=window, signal=signal
    )
    key = (id(signal), handler_name, contexto)
    if _binding_ya_registrado(window, key):
        return

    handler = getattr(window, handler_name, None)
    if callable(handler):
        if signal_pasa_args and not _acepta_argumento(handler):
            logger.error(
                "wiring_handler_invalid_signature",
                extra={
                    "reason_code": _REASON_CODE_FIRMA_INVALIDA,
                    "contexto": contexto,
                    "handler_name": handler_name,
                    "widget": type(window).__name__,
                    "signal": type(signal).__name__,
                },
            )
            raise RuntimeError(f"{handler_name}:{contexto}:firma_invalida")
        signal.connect(handler)
        return

    if _modo_estricto():
        raise RuntimeError(f"{handler_name}:{contexto}")

    logger.error(
        "wiring_handler_missing",
        extra={
            "reason_code": _REASON_CODE_HANDLER_FALTANTE,
            "contexto": contexto,
            "handler_name": handler_name,
            "widget": type(window).__name__,
            "signal": type(signal).__name__,
        },
    )
