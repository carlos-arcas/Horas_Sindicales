from __future__ import annotations

import logging
from pathlib import Path

from app.application.dto import PeriodoFiltro, SolicitudDTO
from app.application.operaciones.exportacion_pdf_historico_operacion import (
    ExportacionPdfHistoricoOperacion,
)
from app.core.metrics import metrics_registry
from app.core.observability import log_event
from app.domain.models import Persona
from app.domain.services import BusinessRuleError


def personas_por_solicitudes(*, solicitudes: list[SolicitudDTO], persona_repo) -> dict[int, Persona]:
    persona_ids = {solicitud.persona_id for solicitud in solicitudes}
    personas: dict[int, Persona] = {}
    if hasattr(persona_repo, "list_all"):
        for persona in persona_repo.list_all(include_inactive=True):
            if persona.id is None:
                continue
            persona_id = int(persona.id)
            if persona_id in persona_ids:
                personas[persona_id] = persona
        if personas:
            return personas
    for persona_id in persona_ids:
        persona_en_repo = persona_repo.get_by_id(persona_id)
        if persona_en_repo is not None:
            personas[persona_id] = persona_en_repo
    return personas


def generar_pdf_historico(
    *,
    solicitudes,
    destino: Path,
    correlation_id: str | None,
    persona_repo,
    config_repo,
    fs,
    generador_pdf,
    obtener_persona_o_error,
    solicitud_to_dto,
    ejecutar_exportacion_pdf_historico,
    pdf_intro_text,
    logger: logging.Logger,
) -> Path:
    solicitudes_list = list(solicitudes)
    if correlation_id:
        log_event(logger, "generar_pdf_historico_started", {"count": len(solicitudes_list)}, correlation_id)
    if not solicitudes_list:
        raise BusinessRuleError("No hay solicitudes para generar el PDF.")
    personas_por_id = personas_por_solicitudes(solicitudes=solicitudes_list, persona_repo=persona_repo)
    persona = obtener_persona_o_error(personas_por_id.get(solicitudes_list[0].persona_id))
    pdf_options = config_repo.get() if config_repo else None
    operacion = ExportacionPdfHistoricoOperacion(fs=fs, generador_pdf=generador_pdf)
    pdf_path = ejecutar_exportacion_pdf_historico(
        operacion=operacion.ejecutar,
        solicitudes=solicitudes_list,
        persona=persona,
        destino=destino,
        personas_por_id=personas_por_id,
        intro_text=pdf_intro_text(pdf_options),
        logo_path=pdf_options.pdf_logo_path if pdf_options else None,
        incrementar_metrica=metrics_registry.incrementar,
        registrar_tiempo=metrics_registry.registrar_tiempo,
    )
    if correlation_id:
        log_event(logger, "generar_pdf_historico_succeeded", {"path": str(pdf_path)}, correlation_id)
    return pdf_path


def exportar_historico_pdf(
    *,
    persona_id: int,
    filtro: PeriodoFiltro,
    destino: Path,
    correlation_id: str | None,
    persona_repo,
    repo,
    config_repo,
    fs,
    generador_pdf,
    obtener_persona_o_error,
    solicitud_to_dto,
    ejecutar_exportacion_pdf_historico,
    pdf_intro_text,
    logger: logging.Logger,
) -> Path:
    if correlation_id:
        log_event(logger, "exportar_historico_pdf_started", {"persona_id": persona_id}, correlation_id)
    persona = obtener_persona_o_error(persona_repo.get_by_id(persona_id))
    solicitudes = repo.list_by_persona_and_period(
        persona_id,
        filtro.year,
        filtro.month if filtro.modo == "MENSUAL" else None,
    )
    solicitudes_list = [solicitud_to_dto(solicitud) for solicitud in solicitudes]
    if not solicitudes_list:
        raise BusinessRuleError("No hay solicitudes para generar el PDF.")
    personas_por_id = personas_por_solicitudes(solicitudes=solicitudes_list, persona_repo=persona_repo)
    pdf_options = config_repo.get() if config_repo else None
    operacion = ExportacionPdfHistoricoOperacion(fs=fs, generador_pdf=generador_pdf)
    pdf_path = ejecutar_exportacion_pdf_historico(
        operacion=operacion.ejecutar,
        solicitudes=solicitudes_list,
        persona=persona,
        destino=destino,
        personas_por_id=personas_por_id,
        intro_text=pdf_intro_text(pdf_options),
        logo_path=pdf_options.pdf_logo_path if pdf_options else None,
        incrementar_metrica=metrics_registry.incrementar,
        registrar_tiempo=metrics_registry.registrar_tiempo,
    )
    if correlation_id:
        log_event(logger, "exportar_historico_pdf_succeeded", {"path": str(pdf_path)}, correlation_id)
    return pdf_path
