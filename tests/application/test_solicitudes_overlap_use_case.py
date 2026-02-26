from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO
from app.domain.models import Persona
from app.domain.services import BusinessRuleError


def _dto(persona_id: int, fecha: str, desde: str | None, hasta: str | None, *, completo: bool = False) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2026-02-20",
        fecha_pedida=fecha,
        desde=desde,
        hasta=hasta,
        completo=completo,
        horas=0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )


def _crear_persona(persona_repo, nombre: str) -> int:
    persona = persona_repo.create(
        Persona(
            id=None,
            nombre=nombre,
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


def test_tramos_contiguos_misma_persona_y_fecha_permitido(solicitud_use_cases, persona_id: int) -> None:
    solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-01", "09:00", "10:00"))

    creada, _ = solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-01", "10:00", "11:00"))

    assert creada.id is not None


def test_solape_misma_persona_y_fecha_bloquea_y_retorna_existing_id(solicitud_use_cases, persona_id: int) -> None:
    solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-01", "09:00", "11:00"))

    candidato = _dto(persona_id, "2026-03-01", "10:00", "12:00")
    duplicate = solicitud_use_cases.buscar_duplicado(candidato)
    assert duplicate is not None
    assert duplicate.id is not None

    with pytest.raises(BusinessRuleError, match="Duplicado"):
        solicitud_use_cases.agregar_solicitud(candidato)


def test_persona_distinta_permitido(solicitud_use_cases, persona_repo, persona_id: int) -> None:
    segunda = _crear_persona(persona_repo, "Delegada 2")
    solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-01", "09:00", "11:00"))

    creada, _ = solicitud_use_cases.agregar_solicitud(_dto(segunda, "2026-03-02", "10:00", "12:00"))

    assert creada.id is not None


def test_misma_persona_fecha_distinta_permitido(solicitud_use_cases, persona_id: int) -> None:
    solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-01", "09:00", "11:00"))

    creada, _ = solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-02", "10:00", "12:00"))

    assert creada.id is not None


def test_completo_colisiona_con_cualquier_parcial_del_dia(solicitud_use_cases, persona_id: int) -> None:
    solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-02", None, None, completo=True))

    candidato = _dto(persona_id, "2026-03-02", "10:00", "12:00")
    assert solicitud_use_cases.buscar_duplicado(candidato) is not None
    with pytest.raises(BusinessRuleError, match="Duplicado|Conflicto completo/parcial"):
        solicitud_use_cases.agregar_solicitud(candidato)
