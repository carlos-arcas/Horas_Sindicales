from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.application.dto import SolicitudDTO
from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto
from app.application.use_cases.confirmacion_pdf.servicio_preflight_pdf import (
    EntradaNombrePdf,
    ServicioPreflightPdf,
)
from app.application.use_cases.solicitudes.auxiliares_caso_uso import (
    NOMBRE_PDF_POR_DEFECTO,
    ResolucionDestinoPdf,
    resolver_destino_pdf,
)
from app.application.use_cases.solicitudes.pdf_destino_policy import (
    resolver_colision_pdf,
    resolver_ruta_sin_colision,
)
from app.domain.ports import PersonaRepository


class ServicioDestinoPdfConfirmacion:
    def __init__(
        self,
        *,
        persona_repo: PersonaRepository,
        fs: SistemaArchivosPuerto,
        generador_pdf: GeneradorPdfPuerto | None,
    ) -> None:
        self._persona_repo = persona_repo
        self._fs = fs
        self._servicio_preflight_pdf = ServicioPreflightPdf(
            fs=fs,
            generador_pdf=generador_pdf,
        )

    def sugerir_nombre_pdf(self, solicitudes: Iterable[SolicitudDTO]) -> str:
        solicitudes_lista = list(solicitudes)
        if not solicitudes_lista:
            return NOMBRE_PDF_POR_DEFECTO
        persona = self._persona_repo.get_by_id(solicitudes_lista[0].persona_id)
        if persona is None:
            raise ValueError("Persona no encontrada.")
        fechas = tuple(solicitud.fecha_pedida for solicitud in solicitudes_lista)
        return self._servicio_preflight_pdf.construir_nombre_pdf(
            EntradaNombrePdf(nombre_persona=persona.nombre, fechas=fechas)
        )

    def resolver_destino_pdf(
        self,
        destino: Path,
        *,
        overwrite: bool = False,
        auto_rename: bool = True,
    ) -> ResolucionDestinoPdf:
        if hasattr(self._fs, "resolver_colision_archivo"):
            resolver_colision = resolver_ruta_sin_colision
        else:

            def resolver_colision(ruta: Path) -> Path:
                return resolver_colision_pdf(ruta, self._fs)

        ruta_destino, colision_detectada, ruta_original, ruta_alternativa = (
            resolver_destino_pdf(
                destino,
                overwrite=overwrite,
                auto_rename=auto_rename,
                resolver_ruta_colision=resolver_colision,
            )
        )
        return ResolucionDestinoPdf(
            ruta_destino=ruta_destino,
            colision_detectada=colision_detectada,
            ruta_original=ruta_original,
            ruta_alternativa=ruta_alternativa if colision_detectada else None,
        )
