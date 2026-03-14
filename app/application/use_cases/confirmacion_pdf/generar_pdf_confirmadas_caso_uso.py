from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.application.dto import SolicitudDTO
from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.application.use_cases.solicitudes.confirmacion_pdf_service import (
    generar_incident_id as _generar_incident_id,
    hash_file as _hash_file,
    pdf_intro_text as _pdf_intro_text,
)
from app.application.use_cases.solicitudes.orquestacion_confirmacion import (
    generar_pdf_confirmadas as generar_pdf_confirmadas_orquestado,
)
from app.application.use_cases.solicitudes.pdf_confirmadas_builder import (
    plan_pdf_confirmadas,
)
from app.application.use_cases.solicitudes.pdf_confirmadas_runner import (
    run_pdf_confirmadas_plan,
)
from app.domain.ports import (
    GrupoConfigRepository,
    PersonaRepository,
    SolicitudRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class GenerarPdfSolicitudesConfirmadasCasoUso:
    repo: SolicitudRepository
    persona_repo: PersonaRepository
    config_repo: GrupoConfigRepository | None = None
    generador_pdf: GeneradorPdfPuerto | None = None

    def generar_pdf_confirmadas(
        self,
        confirmadas: Iterable[SolicitudDTO],
        destino_pdf: Path,
        correlation_id: str | None = None,
    ) -> tuple[Path | None, list[int], str]:
        confirmadas_list = list(confirmadas)
        if not confirmadas_list:
            return None, [], "Sin confirmadas para generar PDF."

        ruta, actualizadas = generar_pdf_confirmadas_orquestado(
            creadas=confirmadas_list,
            destino=destino_pdf,
            config_repo=self.config_repo,
            persona_repo=self.persona_repo,
            generador_pdf=self.generador_pdf,
            repo=self.repo,
            pdf_intro_text=_pdf_intro_text,
            hash_file=_hash_file,
            generar_incident_id=_generar_incident_id,
            planificador_pdf=plan_pdf_confirmadas,
            runner_pdf=run_pdf_confirmadas_plan,
            logger=logger,
            correlation_id=correlation_id,
        )
        if ruta is None:
            return None, [], "No se generó el PDF."
        ids_confirmadas = [sol.id for sol in actualizadas if sol.id is not None]
        return ruta, ids_confirmadas, "OK"

