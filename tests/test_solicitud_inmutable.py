from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import sqlite3

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.domain.models import Persona
from app.infrastructure.migrations import run_migrations
from app.infrastructure.repos_sqlite import PersonaRepositorySQLite, SolicitudRepositorySQLite


def _build_persona() -> Persona:
    return Persona(
        id=None,
        nombre="Delegada Test",
        genero="F",
        horas_mes_min=600,
        horas_ano_min=7200,
        is_active=True,
        cuad_lun_man_min=240,
        cuad_lun_tar_min=240,
        cuad_mar_man_min=240,
        cuad_mar_tar_min=240,
        cuad_mie_man_min=240,
        cuad_mie_tar_min=240,
        cuad_jue_man_min=240,
        cuad_jue_tar_min=240,
        cuad_vie_man_min=240,
        cuad_vie_tar_min=240,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )


def test_dataclasses_replace_en_solicitud_frozen() -> None:
    solicitud = SolicitudDTO(
        id=None,
        persona_id=1,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-15",
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=0.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )

    with pytest.raises(FrozenInstanceError):
        solicitud.horas = 2.0  # type: ignore[misc]

    actualizada = replace(solicitud, horas=2.0)
    assert actualizada.horas == 2.0
    assert solicitud.horas == 0.0


def test_crear_solicitud_incrementa_count_en_repo() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    run_migrations(connection)
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    use_cases = SolicitudUseCases(solicitud_repo, persona_repo)

    persona = persona_repo.create(_build_persona())
    persona_id = persona.id or 0

    before_count = connection.execute(
        "SELECT COUNT(*) FROM solicitudes WHERE persona_id = ? AND (deleted = 0 OR deleted IS NULL)",
        (persona_id,),
    ).fetchone()[0]

    solicitud = SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-15",
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=0.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas="nota",
    )

    creada, _ = use_cases.agregar_solicitud(solicitud)
    assert creada.id is not None

    after_count = connection.execute(
        "SELECT COUNT(*) FROM solicitudes WHERE persona_id = ? AND (deleted = 0 OR deleted IS NULL)",
        (persona_id,),
    ).fetchone()[0]
    assert after_count == before_count + 1

    connection.close()
