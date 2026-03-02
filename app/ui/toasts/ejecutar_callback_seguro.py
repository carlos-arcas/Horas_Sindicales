from __future__ import annotations

from pathlib import Path
import re
from typing import Callable

_PATRON_RUTA_ABSOLUTA = re.compile(r"([A-Za-z]:\\[^\s]+|/[^\s]+)")


def _anonimizar_mensaje_error(mensaje: str) -> str:
    """Redacta rutas absolutas para evitar exposición innecesaria en logs."""

    def _reemplazar(match: re.Match[str]) -> str:
        valor = match.group(0)
        nombre = Path(valor).name
        return f"<ruta:{nombre or 'oculta'}>"

    return _PATRON_RUTA_ABSOLUTA.sub(_reemplazar, mensaje)


def ejecutar_callback_seguro(
    callback: Callable[[], None],
    *,
    logger: object,
    contexto: str,
    correlation_id: str | None,
) -> bool:
    """Ejecuta callbacks de UI sin propagar excepciones al event loop de Qt."""
    try:
        callback()
        return True
    except Exception as exc:  # pragma: no cover - defensivo
        mensaje = _anonimizar_mensaje_error(str(exc))
        logger.error(
            "toast_action_callback_failed",
            extra={
                "contexto": contexto,
                "correlation_id": correlation_id,
                "error_type": type(exc).__name__,
                "error_message": mensaje,
            },
        )
        return False


__all__ = ["ejecutar_callback_seguro"]
