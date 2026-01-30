from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO


def construir_pdf_solicitud(solicitud: SolicitudDTO, destino: Path) -> Path:
    """
    Hook para construir el PDF de una solicitud.

    Actualmente no implementado. Dejar este punto para integrar reportlab.
    """
    raise NotImplementedError("Implementar generación de PDF con reportlab.")
