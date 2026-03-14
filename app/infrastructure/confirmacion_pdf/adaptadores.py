from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.application.use_cases.confirmacion_pdf.puertos import (
    GeneradorPdfConfirmadasPuerto,
    RepositorioSolicitudes,
)


class RepositorioSolicitudesDesdeCasosUso(RepositorioSolicitudes):
    def __init__(self, solicitud_use_cases: SolicitudUseCases) -> None:
        self._solicitud_use_cases = solicitud_use_cases

    def listar_pendientes(self) -> list[SolicitudDTO]:
        return list(self._solicitud_use_cases.listar_pendientes_all())

    def crear_pendiente(
        self, solicitud: SolicitudDTO, correlation_id: str | None = None
    ) -> SolicitudDTO:
        return self._solicitud_use_cases.crear(
            solicitud,
            correlation_id=correlation_id,
        )

    def confirmar_sin_pdf(
        self,
        pendientes: list[SolicitudDTO],
        correlation_id: str | None = None,
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str]]:
        return self._solicitud_use_cases.confirmar_sin_pdf(
            pendientes, correlation_id=correlation_id
        )


class GeneradorPdfConfirmadasDesdeCasosUso(GeneradorPdfConfirmadasPuerto):
    def __init__(self, solicitud_use_cases: SolicitudUseCases) -> None:
        self._solicitud_use_cases = solicitud_use_cases

    def generar_pdf_confirmadas(
        self,
        confirmadas: list[SolicitudDTO],
        destino_pdf: Path,
        correlation_id: str | None = None,
    ) -> tuple[Path | None, list[int], str]:
        return self._solicitud_use_cases.generar_pdf_para_confirmadas(
            confirmadas,
            destino_pdf,
            correlation_id=correlation_id,
        )
