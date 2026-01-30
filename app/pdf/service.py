from __future__ import annotations

from app.application.dto import SolicitudDTO


def generate(solicitudes: list[SolicitudDTO]) -> None:
    """
    Hook para generar PDFs de solicitudes.

    Actualmente no implementado.
    """
    _ = solicitudes
