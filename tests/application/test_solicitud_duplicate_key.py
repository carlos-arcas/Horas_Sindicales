from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO
from app.domain.models import Persona
from app.domain.services import BusinessRuleError


def _build_solicitud(persona_id: int, *, fecha: str, desde: str, hasta: str) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2025-01-01",
        fecha_pedida=fecha,
        desde=desde,
        hasta=hasta,
        completo=False,
        horas=0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )


def test_no_es_duplicado_mismo_dia_horarios_distintos(solicitud_use_cases, persona_id: int) -> None:
    primera = _build_solicitud(persona_id, fecha="2025-01-15", desde="9:00", hasta="11:00")
    segunda = _build_solicitud(persona_id, fecha="2025-01-15", desde="12:00", hasta="13:00")

    solicitud_use_cases.agregar_solicitud(primera)
    creada, _ = solicitud_use_cases.agregar_solicitud(segunda)

    assert creada.id is not None


def test_es_duplicado_solicitud_identica(solicitud_use_cases, persona_id: int) -> None:
    original = _build_solicitud(persona_id, fecha="2025-01-15", desde="9:00", hasta="11:00")
    igual = _build_solicitud(persona_id, fecha="2025-01-15", desde="09:00", hasta="11:00")

    solicitud_use_cases.agregar_solicitud(original)

    with pytest.raises(BusinessRuleError, match="Duplicado"):
        solicitud_use_cases.agregar_solicitud(igual)


def test_no_duplicado_si_dias_distintos_mismo_tramo_misma_delegada(solicitud_use_cases, persona_id: int) -> None:
    primera = _build_solicitud(persona_id, fecha="2026-03-02", desde="17:00", hasta="18:00")
    segunda = _build_solicitud(persona_id, fecha="2026-03-03", desde="17:00", hasta="18:00")

    solicitud_use_cases.agregar_solicitud(primera)
    creada, _ = solicitud_use_cases.agregar_solicitud(segunda)

    assert creada.id is not None


def test_duplicado_si_mismo_dia_mismo_tramo_misma_delegada(solicitud_use_cases, persona_id: int) -> None:
    base = _build_solicitud(persona_id, fecha="2026-03-03", desde="17:00", hasta="18:00")
    solapada = _build_solicitud(persona_id, fecha="2026-03-03", desde="17:30", hasta="18:30")

    solicitud_use_cases.agregar_solicitud(base)

    with pytest.raises(BusinessRuleError, match="Duplicado"):
        solicitud_use_cases.agregar_solicitud(solapada)


def test_no_duplicado_si_mismo_dia_pero_tramos_no_solapan(solicitud_use_cases, persona_id: int) -> None:
    primera = _build_solicitud(persona_id, fecha="2026-03-03", desde="17:00", hasta="18:00")
    segunda = _build_solicitud(persona_id, fecha="2026-03-03", desde="18:00", hasta="19:00")

    solicitud_use_cases.agregar_solicitud(primera)
    creada, _ = solicitud_use_cases.agregar_solicitud(segunda)

    assert creada.id is not None


def test_mismo_tramo_en_distintas_delegadas_es_permitido(solicitud_use_cases, persona_id: int, persona_repo) -> None:
    segunda = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada B",
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
    segunda_id = int(segunda.id or 0)

    original = _build_solicitud(persona_id, fecha="2025-01-15", desde="09:00", hasta="11:00")
    otra_delegada = _build_solicitud(segunda_id, fecha="2025-01-15", desde="09:00", hasta="11:00")

    solicitud_use_cases.agregar_solicitud(original)
    creada, _ = solicitud_use_cases.agregar_solicitud(otra_delegada)

    assert creada.id is not None
