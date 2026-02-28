from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.confirmar_sin_pdf_planner import (
    plan_confirmar_sin_pdf,
)


def _dto(*, solicitud_id: int | None, completo: bool = False) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=1,
        fecha_solicitud="2025-02-01",
        fecha_pedida="2025-02-02",
        desde="09:00",
        hasta="10:00",
        completo=completo,
        horas=1.0,
        observaciones="",
        pdf_path=None,
        pdf_hash=None,
        notas="",
    )


def test_plan_confirmar_sin_pdf_precedencia_id_gana_sobre_valores_falsy() -> None:
    action = plan_confirmar_sin_pdf([_dto(solicitud_id=0)])[0]

    assert action.action_type == "RESOLVE_EXISTING"
    assert action.reason_code == "HAS_ID_RESOLVE_EXISTING"
    assert action.payload.solicitud_id == 0


@pytest.mark.parametrize(
    ("solicitud", "action_type", "reason_code"),
    [
        (_dto(solicitud_id=42), "RESOLVE_EXISTING", "HAS_ID_RESOLVE_EXISTING"),
        (_dto(solicitud_id=0), "RESOLVE_EXISTING", "HAS_ID_RESOLVE_EXISTING"),
        (_dto(solicitud_id=-3), "RESOLVE_EXISTING", "HAS_ID_RESOLVE_EXISTING"),
        (_dto(solicitud_id=None, completo=False), "CREATE_NEW", "MISSING_ID_CREATE_NEW"),
        (_dto(solicitud_id=None, completo=True), "CREATE_NEW", "MISSING_ID_CREATE_NEW"),
    ],
)
def test_plan_confirmar_sin_pdf_reason_code_contrato(
    solicitud: SolicitudDTO,
    action_type: str,
    reason_code: str,
) -> None:
    action = plan_confirmar_sin_pdf([solicitud])[0]

    assert action.action_type == action_type
    assert action.reason_code == reason_code


def test_plan_confirmar_sin_pdf_payload_minimo_para_runner() -> None:
    existente = plan_confirmar_sin_pdf([_dto(solicitud_id=99)])[0]
    nueva = plan_confirmar_sin_pdf([_dto(solicitud_id=None)])[0]

    assert existente.payload.solicitud_id == 99
    assert existente.payload.solicitud is None
    assert nueva.payload.solicitud_id is None
    assert nueva.payload.solicitud is not None


def test_plan_confirmar_sin_pdf_preserva_orden_estable_para_lote() -> None:
    first = _dto(solicitud_id=10)
    second = _dto(solicitud_id=None)
    third = _dto(solicitud_id=0)
    fourth = _dto(solicitud_id=None, completo=True)

    actions = plan_confirmar_sin_pdf([first, second, third, fourth])

    assert [a.action_type for a in actions] == [
        "RESOLVE_EXISTING",
        "CREATE_NEW",
        "RESOLVE_EXISTING",
        "CREATE_NEW",
    ]
    assert [a.solicitud for a in actions] == [first, second, third, fourth]
