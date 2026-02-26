from __future__ import annotations

import sqlite3

import pytest

from app.application.dto import PersonaDTO
from app.application.use_cases import PersonaUseCases
from app.domain.services import BusinessRuleError
from app.infrastructure.migrations import run_migrations
from app.infrastructure.repos_sqlite import PersonaRepositorySQLite


def _build_use_cases() -> PersonaUseCases:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    run_migrations(connection)
    return PersonaUseCases(PersonaRepositorySQLite(connection))


def _persona(nombre: str) -> PersonaDTO:
    return PersonaDTO(
        id=None,
        nombre=nombre,
        genero="F",
        horas_mes=0,
        horas_ano=0,
        is_active=True,
        cuad_lun_man_min=0,
        cuad_lun_tar_min=0,
        cuad_mar_man_min=0,
        cuad_mar_tar_min=0,
        cuad_mie_man_min=0,
        cuad_mie_tar_min=0,
        cuad_jue_man_min=0,
        cuad_jue_tar_min=0,
        cuad_vie_man_min=0,
        cuad_vie_tar_min=0,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )


def test_listar_delegadas_devuelve_ids_estables() -> None:
    use_cases = _build_use_cases()
    p1 = use_cases.crear_persona(_persona("Delegada A"))
    p2 = use_cases.crear_persona(_persona("Delegada B"))

    ids = [persona.id for persona in use_cases.listar_personas()]

    assert p1.id in ids
    assert p2.id in ids
    assert all(persona_id is not None for persona_id in ids)


def test_eliminar_delegada_requiere_id_valido() -> None:
    use_cases = _build_use_cases()

    with pytest.raises(BusinessRuleError):
        use_cases.desactivar_persona(None)  # type: ignore[arg-type]
