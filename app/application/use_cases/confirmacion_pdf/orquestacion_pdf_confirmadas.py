from __future__ import annotations

import logging
from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.pdf_confirmadas_builder import (
    PdfConfirmadasEntrada,
    plan_pdf_confirmadas,
)
from app.application.use_cases.confirmacion_pdf.pdf_confirmadas_runner import run_pdf_confirmadas_plan
from app.application.use_cases.solicitudes.auxiliares_caso_uso import ErrorAplicacionSolicitud


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
