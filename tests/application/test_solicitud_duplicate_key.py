from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO
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
    original = _build_solicitud(persona_id, fecha="2025/01/15", desde="9:00", hasta="11:00")
    igual = _build_solicitud(persona_id, fecha="2025-01-15", desde="09:00", hasta="11:00")

    solicitud_use_cases.agregar_solicitud(original)

    with pytest.raises(BusinessRuleError, match="Duplicado"):
        solicitud_use_cases.agregar_solicitud(igual)
