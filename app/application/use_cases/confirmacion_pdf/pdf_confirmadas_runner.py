from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Protocol, Sequence

from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.pdf_confirmadas_builder import PdfConfirmadasPlan
from app.application.use_cases.confirmacion_pdf.servicio_pdf_confirmadas import actualizar_pdf_en_repo
from app.core.errors import InfraError, PersistenceError
from app.core.metrics import medir_tiempo, metrics_registry
from app.core.observability import log_event
from app.domain.ports import SolicitudRepository
from app.domain.services import BusinessRuleError


class GeneradorPdfSolicitudesPuerto(Protocol):
    def generar_pdf_solicitudes(
        self,
        solicitudes: Sequence[SolicitudDTO],
        persona: object,
        destino: Path,
        *,
        intro_text: str | None = None,
        logo_path: str | None = None,
        include_hours_in_horario: bool | None = None,
    ) -> Path: ...


_MESSAGE_BY_REASON = {
    "PERSONA_NO_ENCONTRADA": "Persona no encontrada.",
    "GENERADOR_NO_CONFIGURADO": "No hay generador PDF configurado.",
}


@medir_tiempo("latency.generar_pdf_ms")
def run_pdf_confirmadas_plan(
    plan: PdfConfirmadasPlan,
    *,
    generador_pdf: GeneradorPdfSolicitudesPuerto | None,
    repo: SolicitudRepository,
    correlation_id: str | None,
    logger: logging.Logger,
    hash_file: Callable[[Path], str],
    incident_id_factory: Callable[[], str],
    app_error_factory: Callable[[str], Exception],
) -> tuple[Path | None, list[SolicitudDTO]]:
    if not plan.actions:
        message = _MESSAGE_BY_REASON.get(plan.reason_code)
        if message is not None:
            raise BusinessRuleError(message)
        return None, []

    pdf_path: Path | None = None
    pdf_hash: str | None = None
    actualizadas: list[SolicitudDTO] = []

    try:
        for action in plan.actions:
            if action.action_type == "GENERATE_PDF":
                if generador_pdf is None or action.destino is None or action.persona is None:
                    raise BusinessRuleError("No hay generador PDF configurado.")
                pdf_path = generador_pdf.generar_pdf_solicitudes(
                    action.solicitudes,
                    action.persona,
                    action.destino,
                    intro_text=action.intro_text,
                    logo_path=action.logo_path,
                    include_hours_in_horario=action.include_hours_in_horario,
                )
                metrics_registry.incrementar("pdfs_generados")
                continue

            if action.action_type == "HASH_FILE":
                if pdf_path is None:
                    continue
                pdf_hash = hash_file(pdf_path)
                continue

            if action.action_type == "UPDATE_STATUS":
                if action.solicitud is None or pdf_path is None:
                    continue
                actualizadas.append(actualizar_pdf_en_repo(repo, action.solicitud, pdf_path, pdf_hash))

        return pdf_path, actualizadas
    except PersistenceError:
        raise
    except InfraError:
        incident_id = incident_id_factory()
        logger.exception("Error técnico generando PDF")
        if correlation_id:
            log_event(
                logger,
                "confirmar_lote_pdf_failed",
                {"error": "generar_pdf", "incident_id": incident_id},
                correlation_id,
            )
        raise app_error_factory(incident_id)
