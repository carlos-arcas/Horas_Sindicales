"""Orquestación de solicitudes para confirmaciones sin ownership del bounded context PDF."""

from __future__ import annotations

import logging
from dataclasses import replace

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.confirmar_sin_pdf_planner import ConfirmarSinPdfAction
from app.core.errors import InfraError
from app.core.observability import log_event


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


__all__ = [
    "confirmar_sin_pdf",
    "run_confirmar_sin_pdf_action",
]
