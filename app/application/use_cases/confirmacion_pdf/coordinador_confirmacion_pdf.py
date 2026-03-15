from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from app.application.dto import SolicitudDTO
from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto
from app.application.use_cases.confirmacion_pdf.orquestacion_confirmacion_pdf import (
    confirmar_lote_y_generar_pdf as confirmar_lote_y_generar_pdf_orquestado,
    generar_pdf_confirmadas as generar_pdf_confirmadas_orquestado,
)
from app.application.use_cases.confirmacion_pdf.pdf_confirmadas_builder import (
    plan_pdf_confirmadas,
)
from app.application.use_cases.confirmacion_pdf.pdf_confirmadas_runner import (
    run_pdf_confirmadas_plan,
)
from app.application.use_cases.confirmacion_pdf.servicio_pdf_confirmadas import (
    generar_incident_id,
    hash_file,
    pdf_intro_text,
)
from app.application.use_cases.confirmacion_pdf.servicio_preflight_pdf import (
    EntradaNombrePdf,
    ServicioPreflightPdf,
)
from app.application.use_cases.solicitudes.auxiliares_caso_uso import (
    NOMBRE_PDF_POR_DEFECTO,
    ResolucionDestinoPdf,
    confirmar_solicitudes_lote_con_manejador,
    resolver_destino_pdf as resolver_destino_pdf_helper,
    resumen_confirmacion_pdf,
    seleccionar_solicitudes_por_filtro,
)
from app.application.use_cases.confirmacion_pdf.orquestacion_compat_solicitudes import (
    confirmar_solicitudes_lote as confirmar_solicitudes_lote_orquestado,
    resolver_o_crear_solicitud as resolver_o_crear_solicitud_orquestado,
)
from app.application.use_cases.solicitudes.pdf_destino_policy import (
    resolver_colision_pdf,
    resolver_ruta_sin_colision,
)
from app.application.use_cases.solicitudes.validaciones import (
    validar_solicitud_dto_declarativo,
)
from app.application.use_cases.solicitudes.mapping_service import (
    solicitud_to_dto as _solicitud_to_dto,
)
from app.domain.ports import GrupoConfigRepository, PersonaRepository, SolicitudRepository


@dataclass
class CoordinadorConfirmacionPdf:
    repo: SolicitudRepository
    persona_repo: PersonaRepository
    fs: SistemaArchivosPuerto
    crear_pendiente: Callable[..., SolicitudDTO]
    config_repo: GrupoConfigRepository | None = None
    generador_pdf: GeneradorPdfPuerto | None = None
    logger: logging.Logger | None = None

    def __post_init__(self) -> None:
        self._logger = self.logger or logging.getLogger(__name__)
        self._servicio_preflight_pdf = ServicioPreflightPdf(
            fs=self.fs,
            generador_pdf=self.generador_pdf,
        )

    def sugerir_nombre_pdf(self, solicitudes: Iterable[SolicitudDTO]) -> str:
        solicitudes_list = list(solicitudes)
        if not solicitudes_list:
            return NOMBRE_PDF_POR_DEFECTO
        persona = self.persona_repo.get_by_id(solicitudes_list[0].persona_id)
        if persona is None:
            raise ValueError("Persona no encontrada.")
        fechas = [solicitud.fecha_pedida for solicitud in solicitudes_list]
        return self._servicio_preflight_pdf.construir_nombre_pdf(
            EntradaNombrePdf(nombre_persona=persona.nombre, fechas=tuple(fechas))
        )

    def resolver_destino_pdf(
        self,
        destino: Path,
        *,
        overwrite: bool = False,
        auto_rename: bool = True,
    ) -> ResolucionDestinoPdf:
        if hasattr(self.fs, "resolver_colision_archivo"):
            resolver_colision = resolver_ruta_sin_colision
        else:

            def resolver_colision(ruta: Path) -> Path:
                return resolver_colision_pdf(ruta, self.fs)

        ruta_destino, colision_detectada, ruta_original, ruta_alternativa = (
            resolver_destino_pdf_helper(
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

    def confirmar_lote_y_generar_pdf(
        self,
        solicitudes: Iterable[SolicitudDTO],
        destino: Path,
        correlation_id: str | None = None,
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str], Path | None]:
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        return confirmar_lote_y_generar_pdf_orquestado(
            solicitudes=solicitudes,
            destino=destino,
            resolver_destino_pdf=self.resolver_destino_pdf,
            fs=self.fs,
            generador_pdf=self.generador_pdf,
            validar_solicitud=validar_solicitud_dto_declarativo,
            confirmar_solicitudes_lote=self._confirmar_solicitudes_lote,
            generar_pdf_confirmadas=self._generar_pdf_confirmadas,
            logger=self._logger,
            correlation_id=correlation_id,
        )

    def confirmar_y_generar_pdf_por_filtro(
        self,
        *,
        filtro_delegada: int | None,
        pendientes: Iterable[SolicitudDTO],
        destino: Path,
        correlation_id: str | None = None,
    ) -> tuple[Path | None, list[int], str]:
        seleccionadas, modo = seleccionar_solicitudes_por_filtro(
            pendientes, filtro_delegada
        )
        if not seleccionadas:
            return None, [], f"Sin pendientes para confirmar ({modo})."

        creadas, _pendientes, errores, ruta = self.confirmar_lote_y_generar_pdf(
            seleccionadas,
            destino,
            correlation_id=correlation_id,
        )
        if ruta is None:
            return None, [], "No se generó el PDF."
        ids_confirmadas = [sol.id for sol in creadas if sol.id is not None]
        resumen = resumen_confirmacion_pdf(creadas, errores, modo)
        return ruta, ids_confirmadas, resumen

    def _confirmar_solicitudes_lote(
        self, solicitudes: list[SolicitudDTO], *, correlation_id: str | None
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str]]:
        return confirmar_solicitudes_lote_orquestado(
            solicitudes=solicitudes,
            resolver_o_crear=self._resolver_o_crear_solicitud,
            confirmar_lote_con_manejador=confirmar_solicitudes_lote_con_manejador,
            generar_incident_id=generar_incident_id,
            logger=self._logger,
            correlation_id=correlation_id,
        )

    def _resolver_o_crear_solicitud(
        self, solicitud: SolicitudDTO, *, correlation_id: str | None
    ) -> SolicitudDTO:
        return resolver_o_crear_solicitud_orquestado(
            solicitud,
            correlation_id=correlation_id,
            get_by_id=self.repo.get_by_id,
            solicitud_to_dto=_solicitud_to_dto,
            crear_pendiente=self.crear_pendiente,
        )

    def _generar_pdf_confirmadas(
        self, creadas: list[SolicitudDTO], destino: Path, *, correlation_id: str | None
    ) -> tuple[Path | None, list[SolicitudDTO]]:
        return generar_pdf_confirmadas_orquestado(
            creadas=creadas,
            destino=destino,
            config_repo=self.config_repo,
            persona_repo=self.persona_repo,
            generador_pdf=self.generador_pdf,
            repo=self.repo,
            pdf_intro_text=pdf_intro_text,
            hash_file=hash_file,
            generar_incident_id=generar_incident_id,
            planificador_pdf=plan_pdf_confirmadas,
            runner_pdf=run_pdf_confirmadas_plan,
            logger=self._logger,
            correlation_id=correlation_id,
        )
