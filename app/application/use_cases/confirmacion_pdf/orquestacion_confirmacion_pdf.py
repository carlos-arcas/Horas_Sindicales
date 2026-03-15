from __future__ import annotations

import logging
from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.operaciones.confirmacion_pdf_operacion import (
    ConfirmacionPdfOperacion,
    RequestConfirmacionPdf,
)
from app.application.use_cases.confirmacion_pdf.orquestacion_pdf_confirmadas import (
    generar_pdf_confirmadas as generar_pdf_confirmadas_feature,
)
from app.core.observability import log_event
from app.domain.services import BusinessRuleError


def confirmar_lote_y_generar_pdf(
    *,
    solicitudes,
    destino: Path,
    resolver_destino_pdf,
    fs,
    generador_pdf,
    validar_solicitud,
    confirmar_solicitudes_lote,
    generar_pdf_confirmadas,
    logger: logging.Logger,
    correlation_id: str | None,
) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str], Path | None]:
    solicitudes_list = list(solicitudes)
    if correlation_id:
        log_event(logger, "confirmar_lote_pdf_started", {"count": len(solicitudes_list)}, correlation_id)

    for solicitud in solicitudes_list:
        validar_solicitud(solicitud)

    resolucion_destino = resolver_destino_pdf(destino, overwrite=False, auto_rename=True)
    destino_resuelto = resolucion_destino.ruta_destino
    if resolucion_destino.colision_detectada and correlation_id:
        log_event(
            logger,
            "pdf_destino_colision_resuelta",
            {
                "reason_code": "PDF_DESTINO_RENOMBRADO_POR_COLISION",
                "ruta_original": str(resolucion_destino.ruta_original),
                "ruta_final": str(destino_resuelto),
            },
            correlation_id,
        )

    preflight = ConfirmacionPdfOperacion(fs=fs, generador_pdf=generador_pdf).ejecutar(
        RequestConfirmacionPdf(
            solicitudes=solicitudes_list,
            destino=destino_resuelto,
            dry_run=True,
            overwrite=False,
        )
    )
    if preflight.conflictos.no_ejecutable:
        raise BusinessRuleError("; ".join(preflight.conflictos.conflictos))

    creadas, pendientes, errores = confirmar_solicitudes_lote(solicitudes_list, correlation_id=correlation_id)
    if errores or not creadas:
        if correlation_id:
            log_event(
                logger,
                "confirmar_lote_pdf_skipped",
                {
                    "creadas": len(creadas),
                    "pendientes": len(pendientes),
                    "errores": len(errores),
                    "motivo": "errores_confirmacion" if errores else "sin_creadas",
                },
                correlation_id,
            )
        return creadas, pendientes, errores, None

    pdf_path, creadas = generar_pdf_confirmadas(creadas, destino_resuelto, correlation_id=correlation_id)

    if correlation_id:
        log_event(
            logger,
            "confirmar_lote_pdf_succeeded",
            {"creadas": len(creadas), "pendientes": len(pendientes), "errores": len(errores)},
            correlation_id,
        )
    return creadas, pendientes, errores, pdf_path


def generar_pdf_confirmadas(
    *,
    creadas: list[SolicitudDTO],
    destino: Path,
    config_repo,
    persona_repo,
    generador_pdf,
    repo,
    pdf_intro_text,
    hash_file,
    generar_incident_id,
    planificador_pdf=None,
    runner_pdf=None,
    logger: logging.Logger,
    correlation_id: str | None,
) -> tuple[Path | None, list[SolicitudDTO]]:
    return generar_pdf_confirmadas_feature(
        creadas=creadas,
        destino=destino,
        config_repo=config_repo,
        persona_repo=persona_repo,
        generador_pdf=generador_pdf,
        repo=repo,
        pdf_intro_text=pdf_intro_text,
        hash_file=hash_file,
        generar_incident_id=generar_incident_id,
        planificador_pdf=planificador_pdf,
        runner_pdf=runner_pdf,
        logger=logger,
        correlation_id=correlation_id,
    )
