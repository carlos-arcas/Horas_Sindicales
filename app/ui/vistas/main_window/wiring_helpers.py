from __future__ import annotations

import logging
import os

from app.ui.copy_catalog import copy_text
from app.ui.qt.slot_seguro import envolver_slot_seguro

logger = logging.getLogger(__name__)

_REASON_CODE_HANDLER_FALTANTE = "WIRING_HANDLER_MISSING"
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


def _build_error_handler_faltante(*, handler_name: str, contexto: str) -> str:
    return copy_text("ui.wiring.handler_missing_detalle").format(
        contexto=contexto,
        handler_name=handler_name,
    )


def conectar_signal(window, signal, handler_name: str, *, contexto: str) -> None:
    key = (id(signal), handler_name, contexto)
    if _binding_ya_registrado(window, key):
        return

    handler = getattr(window, handler_name, None)
    if callable(handler):
        toast = getattr(window, "toast", None)
        slot_seguro = envolver_slot_seguro(
            handler,
            contexto=contexto,
            logger=logger,
            toast=toast,
        )
        signal.connect(slot_seguro)
        return

    mensaje = _build_error_handler_faltante(handler_name=handler_name, contexto=contexto)
    if _modo_estricto():
        raise RuntimeError(mensaje)

    logger.error(
        "wiring_handler_missing",
        extra={
            "reason_code": _REASON_CODE_HANDLER_FALTANTE,
            "contexto": contexto,
            "handler_name": handler_name,
            "detalle": mensaje,
        },
    )
