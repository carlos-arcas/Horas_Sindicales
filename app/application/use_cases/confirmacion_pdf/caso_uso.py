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

    def __call__(self, request: SolicitudConfirmarPdfPeticion) -> SolicitudConfirmarPdfResultado:
        return self.execute(request)

    def execute(
        self, request: SolicitudConfirmarPdfPeticion
    ) -> SolicitudConfirmarPdfResultado:
        self.politica_modo_solo_lectura.verificar()
        correlation_id = request.correlation_id or generate_correlation_id()
        resultado_preflight = self._preflight_o_error(request, correlation_id)
        if resultado_preflight is not None:
            return resultado_preflight

        pendientes_seleccionados, resultado_error = self._cargar_pendientes_o_error(request.pendientes_ids, correlation_id)
        if resultado_error is not None:
            return resultado_error

        if request.generar_pdf:
            return self._confirmar_con_pdf(request, pendientes_seleccionados, correlation_id)
        return self._confirmar_sin_pdf(pendientes_seleccionados, correlation_id)

    def _preflight_o_error(
        self,
        request: SolicitudConfirmarPdfPeticion,
        correlation_id: str,
    ) -> SolicitudConfirmarPdfResultado | None:
        errores = self._validar_preflight(request)
        if not errores:
            return None
        log_event(logger, "confirmacion_pdf_preflight_fallido", {"errores": len(errores)}, correlation_id)
        return SolicitudConfirmarPdfResultado(
            estado="ERROR_PRECONDICION",
            errores=errores,
            sync_permitido=False,
        )

    def _cargar_pendientes_o_error(
        self,
        pendientes_ids: list[int],
        correlation_id: str,
    ) -> tuple[list[SolicitudDTO], SolicitudConfirmarPdfResultado | None]:
        pendientes = self.repositorio.listar_pendientes()
        pendientes_por_id = {
            solicitud.id: solicitud
            for solicitud in pendientes
            if solicitud.id is not None
        }
        return self._seleccionar_pendientes_o_error(pendientes_por_id, pendientes_ids, correlation_id)

    def _confirmar_sin_pdf(
        self,
        pendientes_seleccionados: list[SolicitudDTO],
        correlation_id: str,
    ) -> SolicitudConfirmarPdfResultado:
        _creadas, confirmadas_ids, errores = self._confirmar_pendientes(pendientes_seleccionados, correlation_id)
        restantes = self._listar_pendientes_ids()
        log_event(
            logger,
            "confirmacion_pdf_confirmadas_sin_pdf",
            {
                "confirmadas": len(confirmadas_ids),
                "pendientes_restantes": len(restantes),
                "errores": len(errores),
            },
            correlation_id,
        )
        return self._build_resultado(
            confirmadas_ids=confirmadas_ids,
            errores=errores,
            pendientes_restantes=restantes,
            pdf_generado=None,
        )

    def _confirmar_con_pdf(
        self,
        request: SolicitudConfirmarPdfPeticion,
        pendientes_seleccionados: list[SolicitudDTO],
        correlation_id: str,
    ) -> SolicitudConfirmarPdfResultado:
        assert request.destino_pdf is not None
        self.sistema_archivos.mkdir(
            request.destino_pdf.parent,
            parents=True,
            exist_ok=True,
        )
        creadas, confirmadas_ids, errores_confirmacion = self._confirmar_pendientes(pendientes_seleccionados, correlation_id)
        if errores_confirmacion:
            return self._resultado_post_confirmacion(
                evento="confirmacion_pdf_error_insercion",
                confirmadas_ids=confirmadas_ids,
                errores=errores_confirmacion,
                correlation_id=correlation_id,
            )
        if not confirmadas_ids:
            return self._resultado_post_confirmacion(
                evento="confirmacion_pdf_sin_confirmadas",
                confirmadas_ids=[],
                errores=[],
                correlation_id=correlation_id,
            )
        return self._generar_pdf_y_responder(creadas, request.destino_pdf, correlation_id)

    def _confirmar_pendientes(
        self,
        pendientes_seleccionados: list[SolicitudDTO],
        correlation_id: str,
    ) -> tuple[list[SolicitudDTO], list[int], list[str]]:
        creadas, _pendientes_restantes, errores = self.repositorio.confirmar_sin_pdf(
            pendientes_seleccionados,
            correlation_id=correlation_id,
        )
        confirmadas_ids = [sol.id for sol in creadas if sol.id is not None]
        return creadas, confirmadas_ids, errores

    def _resultado_post_confirmacion(
        self,
        *,
        evento: str,
        confirmadas_ids: list[int],
        errores: list[str],
        correlation_id: str,
    ) -> SolicitudConfirmarPdfResultado:
        restantes = self._listar_pendientes_ids()
        payload = {"pendientes_restantes": len(restantes)}
        if confirmadas_ids:
            payload["confirmadas"] = len(confirmadas_ids)
        if errores:
            payload["errores"] = len(errores)

        log_event(logger, evento, payload, correlation_id)
        return self._build_resultado(
            confirmadas_ids=confirmadas_ids,
            errores=errores,
            pendientes_restantes=restantes,
            pdf_generado=None,
        )

    def _generar_pdf_y_responder(
        self,
        creadas: list[SolicitudDTO],
        destino_pdf,
        correlation_id: str,
    ) -> SolicitudConfirmarPdfResultado:
        ruta_pdf, confirmadas_ids, resumen = self.generador_pdf.generar_pdf_confirmadas(
            creadas,
            destino_pdf=destino_pdf,
            correlation_id=correlation_id,
        )
        errores = [] if confirmadas_ids and ruta_pdf is not None else [resumen]
        restantes = self._listar_pendientes_ids()
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

    def _listar_pendientes_ids(self) -> list[int]:
        return [solicitud.id for solicitud in self.repositorio.listar_pendientes() if solicitud.id is not None]

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
        estado = "OK_SIN_PDF"
        sync_permitido = False
        pdf_resultado = None
        if errores:
            estado = "ERROR_INSERCION" if not confirmadas_ids else "ERROR_PDF"
        elif not confirmadas_ids:
            estado = "SIN_CONFIRMADAS"
        elif pdf_generado is not None:
            estado = "OK_CON_PDF"
            sync_permitido = True
            pdf_resultado = pdf_generado

        return SolicitudConfirmarPdfResultado(
            estado=estado,
            confirmadas=len(confirmadas_ids),
            confirmadas_ids=confirmadas_ids,
            errores=errores,
            pdf_generado=pdf_resultado,
            sync_permitido=sync_permitido,
            pendientes_restantes=pendientes_restantes,
        )
