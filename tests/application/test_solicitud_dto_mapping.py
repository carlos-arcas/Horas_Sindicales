from __future__ import annotations

from app.application.use_cases.solicitudes.use_case import _solicitud_to_dto
from app.domain.models import Solicitud


def test_solicitud_to_dto_preserves_fecha_pedida_and_alias_fecha() -> None:
    solicitud = Solicitud(
        id=10,
        persona_id=4,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-15",
        desde_min=540,
        hasta_min=600,
        completo=False,
        horas_solicitadas_min=60,
        observaciones="obs",
        notas="nota",
    )

    dto = _solicitud_to_dto(solicitud)

    assert dto.fecha_pedida == "2025-01-15"
    assert dto.fecha == "2025-01-01"
