"""Orquestación de solicitudes con wrappers de compatibilidad para flujo PDF confirmadas."""

from __future__ import annotations

import logging
from dataclasses import replace

from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.orquestacion_confirmacion_pdf import (
    confirmar_lote_y_generar_pdf,
    generar_pdf_confirmadas,
)
from app.application.use_cases.solicitudes.confirmar_sin_pdf_planner import ConfirmarSinPdfAction
from app.core.errors import InfraError
from app.core.observability import log_event
from app.domain.services import BusinessRuleError


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
    crear_pendiente,
) -> SolicitudDTO:
    if solicitud.id is not None:
        existente = get_by_id(solicitud.id)
        if existente is None:
            raise BusinessRuleError("La solicitud pendiente ya no existe.")
        return solicitud_to_dto(existente)
    return crear_pendiente(solicitud, correlation_id=correlation_id)


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
    "confirmar_lote_y_generar_pdf",
    "generar_pdf_confirmadas",
    "confirmar_solicitudes_lote",
    "resolver_o_crear_solicitud",
    "confirmar_sin_pdf",
    "run_confirmar_sin_pdf_action",
]
