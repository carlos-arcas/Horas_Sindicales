from __future__ import annotations

from pathlib import Path
from typing import Iterable, Protocol

from app.application.dto import SolicitudDTO
from app.domain.models import Persona


class GeneradorPdfPuerto(Protocol):
    def construir_nombre_archivo(self, nombre_solicitante: str, fechas: Iterable[str]) -> str:
        ...

    def generar_pdf_solicitudes(
        self,
        solicitudes: Iterable[SolicitudDTO],
        persona: Persona,
        destino: Path,
        intro_text: str | None = None,
        logo_path: str | None = None,
        include_hours_in_horario: bool | None = None,
    ) -> Path:
        ...

    def generar_pdf_historico(
        self,
        solicitudes: Iterable[SolicitudDTO],
        persona: Persona,
        destino: Path,
        intro_text: str | None = None,
        logo_path: str | None = None,
    ) -> Path:
        ...
