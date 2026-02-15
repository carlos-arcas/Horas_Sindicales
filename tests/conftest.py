from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application.dto import SolicitudDTO
from app.application.use_cases import PersonaUseCases, SolicitudUseCases
from app.domain.models import Persona
from app.infrastructure.migrations import run_migrations
from app.infrastructure.repos_sqlite import PersonaRepositorySQLite, SolicitudRepositorySQLite


@pytest.fixture
def connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def persona_repo(connection: sqlite3.Connection) -> PersonaRepositorySQLite:
    return PersonaRepositorySQLite(connection)


@pytest.fixture
def solicitud_repo(connection: sqlite3.Connection) -> SolicitudRepositorySQLite:
    return SolicitudRepositorySQLite(connection)


@pytest.fixture
def solicitud_use_cases(
    solicitud_repo: SolicitudRepositorySQLite,
    persona_repo: PersonaRepositorySQLite,
) -> SolicitudUseCases:
    return SolicitudUseCases(solicitud_repo, persona_repo)




@pytest.fixture
def persona_use_cases(persona_repo: PersonaRepositorySQLite) -> PersonaUseCases:
    return PersonaUseCases(persona_repo)


@pytest.fixture
def persona_id(persona_repo: PersonaRepositorySQLite) -> int:
    persona = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada Fixture",
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
    )
    return int(persona.id or 0)


@pytest.fixture
def solicitud_dto(persona_id: int) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-15",
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=2.0,
        observaciones="Obs",
        pdf_path=None,
        pdf_hash=None,
        notas="Nota",
    )
