from __future__ import annotations

from dataclasses import dataclass

from app.application.use_cases.confirmacion_pdf.modelos import SolicitudConfirmarPdfPeticion, SolicitudConfirmarPdfResultado
from app.application.use_cases.confirmacion_pdf.puertos import GeneradorPdfPuerto, RepositorioSolicitudes, SistemaArchivosPuerto


@dataclass
class ConfirmarPendientesPdfCasoUso:
    repositorio: RepositorioSolicitudes
    generador_pdf: GeneradorPdfPuerto
    sistema_archivos: SistemaArchivosPuerto

    def execute(self, request: SolicitudConfirmarPdfPeticion) -> SolicitudConfirmarPdfResultado:
        errores_preflight = self._validar_preflight(request)
        if errores_preflight:
            return SolicitudConfirmarPdfResultado(errores=errores_preflight)

        pendientes = self.repositorio.listar_pendientes()
        pendientes_por_id = {solicitud.id: solicitud for solicitud in pendientes if solicitud.id is not None}
        pendientes_seleccionados = [
            pendientes_por_id[solicitud_id]
            for solicitud_id in request.pendientes_ids
            if solicitud_id in pendientes_por_id
        ]
        faltantes = [solicitud_id for solicitud_id in request.pendientes_ids if solicitud_id not in pendientes_por_id]
        if faltantes:
            return SolicitudConfirmarPdfResultado(
                errores=[f"Pendientes inexistentes: {', '.join(str(item) for item in faltantes)}"],
                pendientes_restantes=sorted(pendientes_por_id),
            )

        if not request.generar_pdf:
            creadas, pendientes_restantes, errores = self.repositorio.confirmar_sin_pdf(
                pendientes_seleccionados,
                correlation_id=request.correlation_id,
            )
            return SolicitudConfirmarPdfResultado(
                confirmadas_ids=[sol.id for sol in creadas if sol.id is not None],
                errores=errores,
                pendientes_restantes=[sol.id for sol in pendientes_restantes if sol.id is not None],
            )

        assert request.destino_pdf is not None
        self.sistema_archivos.mkdir(request.destino_pdf.parent, parents=True, exist_ok=True)
        ruta_pdf, confirmadas_ids, resumen = self.generador_pdf.generar_pdf_pendientes(
            pendientes_seleccionados,
            request.destino_pdf,
            correlation_id=request.correlation_id,
        )
        errores = [] if confirmadas_ids else [resumen]
        restantes = [solicitud_id for solicitud_id in sorted(pendientes_por_id) if solicitud_id not in set(confirmadas_ids)]
        return SolicitudConfirmarPdfResultado(
            confirmadas_ids=confirmadas_ids,
            errores=errores,
            ruta_pdf=ruta_pdf,
            pendientes_restantes=restantes,
        )

    def _validar_preflight(self, request: SolicitudConfirmarPdfPeticion) -> list[str]:
        errores: list[str] = []
        if not request.pendientes_ids:
            errores.append("Selecciona al menos una solicitud pendiente.")
        if request.generar_pdf and request.destino_pdf is None:
            errores.append("Debes indicar una ruta de destino para el PDF.")
        return errores
