from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.confirmar_sin_pdf_planner import (
    plan_confirmar_sin_pdf,
)


def _dto(*, solicitud_id: int | None) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=1,
        fecha_solicitud="2025-02-01",
        fecha_pedida="2025-02-02",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="",
        pdf_path=None,
        pdf_hash=None,
        notas="",
    )


def test_plan_confirmar_sin_pdf_resolve_existing_when_id_exists() -> None:
    action = plan_confirmar_sin_pdf([_dto(solicitud_id=99)])[0]

    assert action.command == "RESOLVE_EXISTING"
    assert action.solicitud.id == 99


def test_plan_confirmar_sin_pdf_create_new_when_id_is_none() -> None:
    action = plan_confirmar_sin_pdf([_dto(solicitud_id=None)])[0]

    assert action.command == "CREATE_NEW"
    assert action.solicitud.id is None


def test_plan_confirmar_sin_pdf_preserva_orden() -> None:
    first = _dto(solicitud_id=10)
    second = _dto(solicitud_id=None)

    actions = plan_confirmar_sin_pdf([first, second])

    assert [a.command for a in actions] == ["RESOLVE_EXISTING", "CREATE_NEW"]
    assert [a.solicitud for a in actions] == [first, second]
