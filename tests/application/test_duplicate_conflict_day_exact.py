from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO
from app.domain.models import Solicitud
from app.domain.services import BusinessRuleError


def _dto(persona_id: int, fecha: str, desde: str, hasta: str) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2026-02-20",
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


def test_no_duplicada_si_misma_persona_mismo_tramo_pero_dias_distintos(solicitud_use_cases, persona_id: int) -> None:
    solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-01", "09:00", "10:00"))

    creada, _ = solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-02", "09:00", "10:00"))

    assert creada.id is not None


def test_duplicada_si_misma_persona_misma_fecha_y_tramo_solapado(solicitud_use_cases, persona_id: int) -> None:
    solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-01", "09:00", "10:00"))

    with pytest.raises(BusinessRuleError, match="Duplicado"):
        solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-01", "09:30", "10:30"))


def test_no_duplicada_si_solo_tocan_borde_en_misma_fecha(solicitud_use_cases, persona_id: int) -> None:
    solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-01", "09:00", "10:00"))

    creada, _ = solicitud_use_cases.agregar_solicitud(_dto(persona_id, "2026-03-01", "10:00", "11:00"))

    assert creada.id is not None


def test_regresion_no_confunde_dias_distintos_con_fecha_en_datetime_db(solicitud_repo, persona_id: int) -> None:
    solicitud_repo.create(
        Solicitud(
            id=None,
            persona_id=persona_id,
            fecha_solicitud="2026-03-01",
            fecha_pedida="2026-03-01T23:30:00-02:00",
            desde_min=9 * 60,
            hasta_min=10 * 60,
            completo=False,
            horas_solicitadas_min=60,
            observaciones=None,
            notas=None,
            pdf_path=None,
            pdf_hash=None,
            generated=True,
        )
    )

    duplicada = solicitud_repo.find_duplicate(
        persona_id=persona_id,
        fecha_pedida="2026-03-02",
        desde_min=9 * 60,
        hasta_min=10 * 60,
        completo=False,
    )

    assert duplicada is None
