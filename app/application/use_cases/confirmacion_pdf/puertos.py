from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.application.dto import SolicitudDTO
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto


class RepositorioSolicitudes(Protocol):
    def crear_pendiente(self, solicitud: SolicitudDTO, correlation_id: str | None = None) -> SolicitudDTO: ...

    def listar_pendientes(self) -> list[SolicitudDTO]: ...

    def confirmar_sin_pdf(self, pendientes: list[SolicitudDTO], correlation_id: str | None = None) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str]]: ...

    def confirmar_con_pdf(
        self,
        pendientes: list[SolicitudDTO],
        destino_pdf: Path,
        correlation_id: str | None = None,
    ) -> tuple[Path | None, list[int], str]: ...


class GeneradorPdfPuerto(Protocol):
    def generar_pdf_pendientes(self, pendientes: list[SolicitudDTO], destino: Path, correlation_id: str | None = None) -> tuple[Path | None, list[int], str]: ...


__all__ = ["RepositorioSolicitudes", "GeneradorPdfPuerto", "SistemaArchivosPuerto"]
