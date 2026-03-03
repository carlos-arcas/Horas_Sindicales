from __future__ import annotations

from dataclasses import dataclass
import logging

from app.core.observability import generate_correlation_id, log_event
from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.modelos import SolicitudConfirmarPdfPeticion, SolicitudConfirmarPdfResultado
from app.application.use_cases.confirmacion_pdf.puertos import GeneradorPdfPuerto, RepositorioSolicitudes, SistemaArchivosPuerto


logger = logging.getLogger(__name__)


@dataclass
class ConfirmarPendientesPdfCasoUso:
    repositorio: RepositorioSolicitudes
    generador_pdf: GeneradorPdfPuerto
    sistema_archivos: SistemaArchivosPuerto

    def __call__(self, request: SolicitudConfirmarPdfPeticion) -> SolicitudConfirmarPdfResultado:
        return self.execute(request)

    def execute(self, request: SolicitudConfirmarPdfPeticion) -> SolicitudConfirmarPdfResultado:
        correlation_id = request.correlation_id or generate_correlation_id()
        errores_preflight = self._validar_preflight(request)
        if errores_preflight:
            log_event(
                logger,
                "confirmacion_pdf_preflight_fallido",
                {"errores": len(errores_preflight)},
                correlation_id,
            )
            return SolicitudConfirmarPdfResultado(errores=errores_preflight)

        pendientes = self.repositorio.listar_pendientes()
        pendientes_por_id = {solicitud.id: solicitud for solicitud in pendientes if solicitud.id is not None}
        pendientes_seleccionados, resultado_error = self._seleccionar_pendientes_o_error(
            pendientes_por_id,
            request.pendientes_ids,
            correlation_id,
        )
        if resultado_error is not None:
            return resultado_error

        if not request.generar_pdf:
            creadas, _pendientes_restantes, errores = self.repositorio.confirmar_sin_pdf(
                pendientes_seleccionados,
                correlation_id=correlation_id,
            )
            pendientes_actuales = self.repositorio.listar_pendientes()
            log_event(
                logger,
                "confirmacion_pdf_confirmadas_sin_pdf",
                {
                    "confirmadas": len(creadas),
                    "pendientes_restantes": len(pendientes_actuales),
                    "errores": len(errores),
                },
                correlation_id,
            )
            return SolicitudConfirmarPdfResultado(
                confirmadas_ids=[sol.id for sol in creadas if sol.id is not None],
                errores=errores,
                pendientes_restantes=[sol.id for sol in pendientes_actuales if sol.id is not None],
            )

        assert request.destino_pdf is not None
        self.sistema_archivos.mkdir(request.destino_pdf.parent, parents=True, exist_ok=True)
        ruta_pdf, confirmadas_ids, resumen = self.repositorio.confirmar_con_pdf(
            pendientes_seleccionados,
            destino_pdf=request.destino_pdf,
            correlation_id=correlation_id,
        )
        errores = [] if confirmadas_ids else [resumen]
        restantes = [solicitud_id for solicitud_id in sorted(pendientes_por_id) if solicitud_id not in set(confirmadas_ids)]
        log_event(
            logger,
            "confirmacion_pdf_confirmadas_con_pdf",
            {
                "confirmadas": len(confirmadas_ids),
                "pendientes_restantes": len(restantes),
                "ruta_pdf": str(ruta_pdf) if ruta_pdf else None,
            },
            correlation_id,
        )
        return SolicitudConfirmarPdfResultado(
            confirmadas_ids=confirmadas_ids,
            errores=errores,
            ruta_pdf=ruta_pdf,
            pendientes_restantes=restantes,
        )

    def _seleccionar_pendientes_o_error(
        self,
        pendientes_por_id: dict[int, SolicitudDTO],
        pendientes_ids: list[int],
        correlation_id: str,
    ) -> tuple[list[SolicitudDTO], SolicitudConfirmarPdfResultado | None]:
        pendientes_seleccionados = [
            pendientes_por_id[solicitud_id]
            for solicitud_id in pendientes_ids
            if solicitud_id in pendientes_por_id
        ]
        faltantes = [solicitud_id for solicitud_id in pendientes_ids if solicitud_id not in pendientes_por_id]
        if not faltantes:
            return pendientes_seleccionados, None

        log_event(
            logger,
            "confirmacion_pdf_pendientes_inexistentes",
            {"faltantes": faltantes},
            correlation_id,
        )
        return pendientes_seleccionados, SolicitudConfirmarPdfResultado(
            errores=[f"Pendientes inexistentes: {', '.join(str(item) for item in faltantes)}"],
            pendientes_restantes=sorted(pendientes_por_id),
        )

    def _validar_preflight(self, request: SolicitudConfirmarPdfPeticion) -> list[str]:
        errores: list[str] = []
        if not request.pendientes_ids:
            errores.append("Selecciona al menos una solicitud pendiente.")
        if request.generar_pdf and request.destino_pdf is None:
            errores.append("Debes indicar una ruta de destino para el PDF.")
        return errores
