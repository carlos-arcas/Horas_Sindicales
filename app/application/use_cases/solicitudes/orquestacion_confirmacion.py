from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from app.application.dto import SolicitudDTO
from app.application.operaciones.confirmacion_pdf_operacion import (
    ConfirmacionPdfOperacion,
    RequestConfirmacionPdf,
)
from app.application.use_cases.solicitudes.auxiliares_caso_uso import ErrorAplicacionSolicitud
from app.application.use_cases.solicitudes.confirmar_sin_pdf_planner import ConfirmarSinPdfAction
from app.application.use_cases.solicitudes.pdf_confirmadas_builder import (
    PdfConfirmadasEntrada,
    plan_pdf_confirmadas,
)
from app.application.use_cases.solicitudes.pdf_confirmadas_runner import run_pdf_confirmadas_plan
from app.core.errors import InfraError
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


def confirmar_solicitudes_lote(
    *,
    solicitudes: list[SolicitudDTO],
    resolver_o_crear,
    confirmar_lote_con_manejador,
    generar_incident_id,
    logger: logging.Logger,
    correlation_id: str | None,
) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str]]:
    def _construir_error_infra() -> str:
        incident_id = generar_incident_id()
        logger.exception("Error técnico creando solicitud")
        if correlation_id:
            log_event(
                logger,
                "confirmar_lote_pdf_failed",
                {"error": "crear_solicitud", "incident_id": incident_id},
                correlation_id,
            )
        return f"Se produjo un error técnico al guardar la solicitud. ID de incidente: {incident_id}"

    return confirmar_lote_con_manejador(
        solicitudes,
        resolver_o_crear=lambda solicitud: resolver_o_crear(solicitud, correlation_id=correlation_id),
        construir_error_infra=_construir_error_infra,
    )


def resolver_o_crear_solicitud(
    solicitud: SolicitudDTO,
    *,
    correlation_id: str | None,
    get_by_id,
    solicitud_to_dto,
    agregar_solicitud,
) -> SolicitudDTO:
    if solicitud.id is not None:
        existente = get_by_id(solicitud.id)
        if existente is None:
            raise BusinessRuleError("La solicitud pendiente ya no existe.")
        return solicitud_to_dto(existente)
    creada, _ = agregar_solicitud(solicitud, correlation_id=correlation_id)
    return creada


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
    planificador_pdf=plan_pdf_confirmadas,
    runner_pdf=run_pdf_confirmadas_plan,
    logger: logging.Logger,
    correlation_id: str | None,
) -> tuple[Path | None, list[SolicitudDTO]]:
    pdf_options = config_repo.get() if config_repo else None
    entrada = PdfConfirmadasEntrada(
        creadas=tuple(creadas),
        destino=destino,
        persona=persona_repo.get_by_id(creadas[0].persona_id) if creadas else None,
        generador_configurado=generador_pdf is not None,
        intro_text=pdf_intro_text(pdf_options),
        logo_path=pdf_options.pdf_logo_path if pdf_options else None,
        include_hours_in_horario=(pdf_options.pdf_include_hours_in_horario if pdf_options else None),
    )
    plan = planificador_pdf(entrada)
    pdf_path, actualizadas = runner_pdf(
        plan,
        generador_pdf=generador_pdf,
        repo=repo,
        correlation_id=correlation_id,
        logger=logger,
        hash_file=hash_file,
        incident_id_factory=generar_incident_id,
        app_error_factory=lambda incident_id: ErrorAplicacionSolicitud(
            "No se pudo generar el PDF por un error técnico",
            incident_id=incident_id,
        ),
    )
    if pdf_path is None:
        return None, creadas
    return pdf_path, actualizadas


def confirmar_sin_pdf(
    *,
    solicitudes,
    planner,
    run_action,
    confirmar_sin_pdf_con_manejador,
    logger: logging.Logger,
    correlation_id: str | None,
) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str]]:
    solicitudes_list = list(solicitudes)
    if correlation_id:
        log_event(logger, "confirmar_sin_pdf_started", {"count": len(solicitudes_list)}, correlation_id)

    plan = planner(solicitudes_list)

    def _construir_error_infra(exc: InfraError) -> str:
        logger.exception("Error técnico confirmando solicitud sin PDF")
        if correlation_id:
            log_event(logger, "confirmar_sin_pdf_failed", {"error": str(exc)}, correlation_id)
        return "Se produjo un error técnico al confirmar la solicitud."

    creadas_confirmadas, pendientes_restantes, errores = confirmar_sin_pdf_con_manejador(
        plan,
        ejecutar_accion=lambda action: run_action(action, correlation_id=correlation_id),
        obtener_solicitud=lambda action: action.solicitud,
        construir_error_infra=_construir_error_infra,
    )

    if correlation_id:
        log_event(
            logger,
            "confirmar_sin_pdf_succeeded",
            {"creadas": len(creadas_confirmadas), "pendientes": len(pendientes_restantes), "errores": len(errores)},
            correlation_id,
        )
    return creadas_confirmadas, pendientes_restantes, errores


def run_confirmar_sin_pdf_action(
    action: ConfirmarSinPdfAction,
    *,
    correlation_id: str | None,
    ejecutar_confirmar_sin_pdf_action,
    get_by_id,
    solicitud_to_dto,
    agregar_solicitud,
    marcar_generada,
) -> SolicitudDTO:
    creada = ejecutar_confirmar_sin_pdf_action(
        action.action_type,
        action.payload.solicitud_id,
        action.payload.solicitud,
        obtener_existente=lambda solicitud_id: (
            solicitud_to_dto(existente) if (existente := get_by_id(solicitud_id)) else None
        ),
        agregar_solicitud=lambda solicitud: agregar_solicitud(
            solicitud,
            correlation_id=correlation_id,
        )[0],
        marcar_generada=marcar_generada,
    )
    return replace(creada, generated=True)
