from __future__ import annotations

from collections.abc import Callable
from pathlib import PurePath
from typing import Any

from app.core.redactor_secretos import redactar_texto


def _normalizar_contexto(contexto: str) -> str:
    contexto_redactado = redactar_texto(contexto.strip())
    if not contexto_redactado:
        return "toast.action"

    if "/" not in contexto_redactado and "\\" not in contexto_redactado:
        return contexto_redactado

    path = PurePath(contexto_redactado)
    partes = [parte for parte in path.parts if parte not in {"/", "\\"}]
    if len(partes) <= 2:
        return "/".join(partes)
    return ".../" + "/".join(partes[-2:])


def ejecutar_callback_seguro(
    callback: Callable[[], Any] | None,
    *,
    logger: Any,
    contexto: str,
    correlation_id: str | None,
) -> bool:
    if callback is None:
        return False

    contexto_seguro = _normalizar_contexto(contexto)
    try:
        callback()
        return True
    except Exception:
        logger.exception(
            "toast_action_callback_failed",
            extra={
                "contexto": contexto_seguro,
                "correlation_id": correlation_id,
            },
        )
        return False


__all__ = [ejecutar_callback_seguro.__name__]
