from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.application.dto import SolicitudDTO
from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.domain.models import Persona
from app.pdf import pdf_builder


class GeneradorPdfReportlab(GeneradorPdfPuerto):
    def construir_nombre_archivo(self, nombre_solicitante: str, fechas: Iterable[str]) -> str:
        return pdf_builder.build_nombre_archivo(nombre_solicitante, fechas)

    def generar_pdf_solicitudes(
        self,
        solicitudes: Iterable[SolicitudDTO],
        persona: Persona,
        destino: Path,
        intro_text: str | None = None,
        logo_path: str | None = None,
        include_hours_in_horario: bool | None = None,
    ) -> Path:
        return pdf_builder.construir_pdf_solicitudes(
            solicitudes,
            persona,
            destino,
            intro_text=intro_text,
            logo_path=logo_path,
            include_hours_in_horario=include_hours_in_horario,
        )

    def generar_pdf_historico(
        self,
        solicitudes: Iterable[SolicitudDTO],
        persona: Persona,
        destino: Path,
        intro_text: str | None = None,
        logo_path: str | None = None,
    ) -> Path:
        return pdf_builder.construir_pdf_historico(
            solicitudes,
            persona,
            destino,
            intro_text=intro_text,
            logo_path=logo_path,
        )
