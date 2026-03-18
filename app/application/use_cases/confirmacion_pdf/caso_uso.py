from __future__ import annotations

from dataclasses import dataclass
import logging

from app.core.observability import generate_correlation_id, log_event
from app.application.dto import SolicitudDTO
from app.application.use_cases.politica_modo_solo_lectura import (
    PoliticaModoSoloLectura,
)
from app.application.use_cases.confirmacion_pdf.modelos import (
    SolicitudConfirmarPdfPeticion,
    SolicitudConfirmarPdfResultado,
)
from app.application.use_cases.confirmacion_pdf.puertos import (
    GeneradorPdfConfirmadasPuerto,
    RepositorioSolicitudes,
    SistemaArchivosPuerto,
)


logger = logging.getLogger(__name__)


@dataclass
class ConfirmarPendientesPdfCasoUso:
    repositorio: RepositorioSolicitudes
    generador_pdf: GeneradorPdfConfirmadasPuerto
    sistema_archivos: SistemaArchivosPuerto
    politica_modo_solo_lectura: PoliticaModoSoloLectura

    def __call__(
        self, request: SolicitudConfirmarPdfPeticion
    ) -> SolicitudConfirmarPdfResultado:
        return self.execute(request)

    def execute(
        self, request: SolicitudConfirmarPdfPeticion
    ) -> SolicitudConfirmarPdfResultado:
        self.politica_modo_solo_lectura.verificar()
        correlation_id = request.correlation_id or generate_correlation_id()
        errores_preflight = self._validar_preflight(request)
        if errores_preflight:
            log_event(
                logger,
                "confirmacion_pdf_preflight_fallido",
                {"errores": len(errores_preflight)},
                correlation_id,
            )
            return SolicitudConfirmarPdfResultado(
                estado="ERROR_PRECONDICION",
                errores=errores_preflight,
                sync_permitido=False,
            )

        pendientes = self.repositorio.listar_pendientes()
        pendientes_por_id = {
            solicitud.id: solicitud
            for solicitud in pendientes
            if solicitud.id is not None
        }
        pendientes_seleccionados, resultado_error = (
            self._seleccionar_pendientes_o_error(
                pendientes_por_id,
                request.pendientes_ids,
                correlation_id,
            )
        )
        if resultado_error is not None:
            return resultado_error

        if not request.generar_pdf:
            creadas, _pendientes_restantes, errores = (
                self.repositorio.confirmar_sin_pdf(
                    pendientes_seleccionados,
                    correlation_id=correlation_id,
                )
            )
            pendientes_actuales = self.repositorio.listar_pendientes()
            confirmadas_ids = [sol.id for sol in creadas if sol.id is not None]
            log_event(
                logger,
                "confirmacion_pdf_confirmadas_sin_pdf",
                {
                    "confirmadas": len(confirmadas_ids),
                    "pendientes_restantes": len(pendientes_actuales),
                    "errores": len(errores),
                },
                correlation_id,
            )
            return self._build_resultado(
                confirmadas_ids=confirmadas_ids,
                errores=errores,
                pendientes_restantes=[
                    sol.id for sol in pendientes_actuales if sol.id is not None
                ],
                pdf_generado=None,
            )

        assert request.destino_pdf is not None
        self.sistema_archivos.mkdir(
            request.destino_pdf.parent, parents=True, exist_ok=True
        )
        creadas, _pendientes_restantes, errores_confirmacion = (
            self.repositorio.confirmar_sin_pdf(
                pendientes_seleccionados,
                correlation_id=correlation_id,
            )
        )
        confirmadas_ids = [sol.id for sol in creadas if sol.id is not None]
        if errores_confirmacion:
            pendientes_actuales = self.repositorio.listar_pendientes()
            restantes = [sol.id for sol in pendientes_actuales if sol.id is not None]
            log_event(
                logger,
                "confirmacion_pdf_error_insercion",
                {
                    "confirmadas": len(confirmadas_ids),
                    "pendientes_restantes": len(restantes),
                    "errores": len(errores_confirmacion),
                },
                correlation_id,
            )
            return self._build_resultado(
                confirmadas_ids=confirmadas_ids,
                errores=errores_confirmacion,
                pendientes_restantes=restantes,
                pdf_generado=None,
            )

        if not confirmadas_ids:
            pendientes_actuales = self.repositorio.listar_pendientes()
            restantes = [sol.id for sol in pendientes_actuales if sol.id is not None]
            log_event(
                logger,
                "confirmacion_pdf_sin_confirmadas",
                {"pendientes_restantes": len(restantes)},
                correlation_id,
            )
            return self._build_resultado(
                confirmadas_ids=[],
                errores=[],
                pendientes_restantes=restantes,
                pdf_generado=None,
            )

        ruta_pdf, confirmadas_ids, resumen = self.generador_pdf.generar_pdf_confirmadas(
            creadas,
            destino_pdf=request.destino_pdf,
            correlation_id=correlation_id,
        )
        errores = [] if confirmadas_ids and ruta_pdf is not None else [resumen]
        pendientes_actuales = self.repositorio.listar_pendientes()
        restantes = [sol.id for sol in pendientes_actuales if sol.id is not None]
        log_event(
            logger,
            "confirmacion_pdf_confirmadas_con_pdf",
            {
                "confirmadas": len(confirmadas_ids),
                "pendientes_restantes": len(restantes),
                "ruta_pdf": str(ruta_pdf) if ruta_pdf else None,
                "errores": len(errores),
            },
            correlation_id,
        )
        return self._build_resultado(
            confirmadas_ids=confirmadas_ids,
            errores=errores,
            pendientes_restantes=restantes,
            pdf_generado=ruta_pdf if not errores else None,
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
        faltantes = [
            solicitud_id
            for solicitud_id in pendientes_ids
            if solicitud_id not in pendientes_por_id
        ]
        if not faltantes:
            return pendientes_seleccionados, None

        log_event(
            logger,
            "confirmacion_pdf_pendientes_inexistentes",
            {"faltantes": faltantes},
            correlation_id,
        )
        return pendientes_seleccionados, SolicitudConfirmarPdfResultado(
            estado="ERROR_PRECONDICION",
            errores=[
                f"Pendientes inexistentes: {', '.join(str(item) for item in faltantes)}"
            ],
            pendientes_restantes=sorted(pendientes_por_id),
            sync_permitido=False,
        )

    def _validar_preflight(self, request: SolicitudConfirmarPdfPeticion) -> list[str]:
        errores: list[str] = []
        if not request.pendientes_ids:
            errores.append("Selecciona al menos una solicitud pendiente.")
        if request.generar_pdf and request.destino_pdf is None:
            errores.append("Debes indicar una ruta de destino para el PDF.")
        return errores

    def _build_resultado(
        self,
        *,
        confirmadas_ids: list[int],
        errores: list[str],
        pendientes_restantes: list[int],
        pdf_generado,
    ) -> SolicitudConfirmarPdfResultado:
        if errores:
            estado = "ERROR_INSERCION" if not confirmadas_ids else "ERROR_PDF"
            return SolicitudConfirmarPdfResultado(
                estado=estado,
                confirmadas=len(confirmadas_ids),
                confirmadas_ids=confirmadas_ids,
                errores=errores,
                pdf_generado=None,
                sync_permitido=False,
                pendientes_restantes=pendientes_restantes,
            )
        if not confirmadas_ids:
            return SolicitudConfirmarPdfResultado(
                estado="SIN_CONFIRMADAS",
                confirmadas=0,
                confirmadas_ids=[],
                errores=[],
                pdf_generado=None,
                sync_permitido=False,
                pendientes_restantes=pendientes_restantes,
            )
        if pdf_generado is not None:
            return SolicitudConfirmarPdfResultado(
                estado="OK_CON_PDF",
                confirmadas=len(confirmadas_ids),
                confirmadas_ids=confirmadas_ids,
                errores=[],
                pdf_generado=pdf_generado,
                sync_permitido=True,
                pendientes_restantes=pendientes_restantes,
            )
        return SolicitudConfirmarPdfResultado(
            estado="OK_SIN_PDF",
            confirmadas=len(confirmadas_ids),
            confirmadas_ids=confirmadas_ids,
            errores=[],
            pdf_generado=None,
            sync_permitido=False,
            pendientes_restantes=pendientes_restantes,
        )
