"""Compatibilidad interna para reutilizar orquestación de solicitudes desde confirmación PDF."""

from __future__ import annotations

import logging

from app.application.dto import SolicitudDTO
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


__all__ = ["confirmar_solicitudes_lote", "resolver_o_crear_solicitud"]
