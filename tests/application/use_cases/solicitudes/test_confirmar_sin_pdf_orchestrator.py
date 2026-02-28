from __future__ import annotations

from dataclasses import replace
from unittest.mock import Mock

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.confirmar_sin_pdf_planner import (
    ConfirmarSinPdfAction,
    ConfirmarSinPdfPayload,
)
from app.application.use_cases.solicitudes.use_case import SolicitudUseCases
from app.core.errors import InfraError, PersistenceError
from app.domain.services import BusinessRuleError, ValidacionError


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


def _build_action(solicitud: SolicitudDTO) -> ConfirmarSinPdfAction:
    has_id = solicitud.id is not None
    return ConfirmarSinPdfAction(
        action_type="RESOLVE_EXISTING" if has_id else "CREATE_NEW",
        reason_code="HAS_ID_RESOLVE_EXISTING" if has_id else "MISSING_ID_CREATE_NEW",
        payload=(
            ConfirmarSinPdfPayload(solicitud_id=solicitud.id)
            if has_id
            else ConfirmarSinPdfPayload(solicitud=solicitud)
        ),
        source_solicitud=solicitud,
    )


def _use_case() -> SolicitudUseCases:
    return SolicitudUseCases(repo=Mock(), persona_repo=Mock())


def test_confirmar_sin_pdf_invoca_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = _use_case()
    solicitudes = [_dto(solicitud_id=10)]
    planner_called = {}

    def _fake_planner(received: list[SolicitudDTO]):
        planner_called["items"] = received
        return tuple(_build_action(item) for item in received)

    monkeypatch.setattr("app.application.use_cases.solicitudes.use_case.plan_confirmar_sin_pdf", _fake_planner)
    monkeypatch.setattr(use_case, "_run_confirmar_sin_pdf_action", lambda action, correlation_id: action.solicitud)

    use_case.confirmar_sin_pdf(solicitudes)

    assert planner_called["items"] == solicitudes


def test_confirmar_sin_pdf_ejecuta_runner_en_orden(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = _use_case()
    solicitudes = [_dto(solicitud_id=1), _dto(solicitud_id=None), _dto(solicitud_id=2)]
    actions = tuple(_build_action(item) for item in solicitudes)
    monkeypatch.setattr("app.application.use_cases.solicitudes.use_case.plan_confirmar_sin_pdf", lambda _: actions)

    seen_order: list[int | None] = []

    def _fake_run(action: ConfirmarSinPdfAction, *, correlation_id: str | None):
        seen_order.append(action.solicitud.id)
        return replace(action.solicitud, generated=True)

    monkeypatch.setattr(use_case, "_run_confirmar_sin_pdf_action", _fake_run)

    creadas, pendientes, errores = use_case.confirmar_sin_pdf(solicitudes)

    assert seen_order == [1, None, 2]
    assert [dto.generated for dto in creadas] == [True, True, True]
    assert pendientes == []
    assert errores == []


def test_confirmar_sin_pdf_propagates_persistence_error(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = _use_case()
    solicitudes = [_dto(solicitud_id=1)]
    monkeypatch.setattr(
        "app.application.use_cases.solicitudes.use_case.plan_confirmar_sin_pdf",
        lambda _: (_build_action(solicitudes[0]),),
    )

    def _raise(*_args, **_kwargs):
        raise PersistenceError("db down")

    monkeypatch.setattr(use_case, "_run_confirmar_sin_pdf_action", _raise)

    with pytest.raises(PersistenceError, match="db down"):
        use_case.confirmar_sin_pdf(solicitudes)


def test_confirmar_sin_pdf_mantiene_manejo_errores_funcionales_e_infra(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = _use_case()
    one = _dto(solicitud_id=1)
    two = _dto(solicitud_id=None)
    actions = (_build_action(one), _build_action(two))
    monkeypatch.setattr("app.application.use_cases.solicitudes.use_case.plan_confirmar_sin_pdf", lambda _: actions)

    calls = iter([ValidacionError("faltan datos"), InfraError("socket timeout")])

    def _fake_run(action: ConfirmarSinPdfAction, *, correlation_id: str | None):
        result = next(calls)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(use_case, "_run_confirmar_sin_pdf_action", _fake_run)

    creadas, pendientes, errores = use_case.confirmar_sin_pdf([one, two])

    assert creadas == []
    assert pendientes == [one, two]
    assert errores == [
        "faltan datos",
        "Se produjo un error técnico al confirmar la solicitud.",
    ]


def test_confirmar_sin_pdf_sin_side_effects_con_plan_vacio(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = _use_case()
    run_mock = Mock()
    monkeypatch.setattr("app.application.use_cases.solicitudes.use_case.plan_confirmar_sin_pdf", lambda _: tuple())
    monkeypatch.setattr(use_case, "_run_confirmar_sin_pdf_action", run_mock)

    creadas, pendientes, errores = use_case.confirmar_sin_pdf([])

    assert creadas == []
    assert pendientes == []
    assert errores == []
    run_mock.assert_not_called()


def test_confirmar_sin_pdf_business_error_se_reporta_igual_que_validacion(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = _use_case()
    solicitud = _dto(solicitud_id=77)
    monkeypatch.setattr(
        "app.application.use_cases.solicitudes.use_case.plan_confirmar_sin_pdf",
        lambda _: (_build_action(solicitud),),
    )

    def _raise(*_args, **_kwargs):
        raise BusinessRuleError("La solicitud pendiente ya no existe.")

    monkeypatch.setattr(use_case, "_run_confirmar_sin_pdf_action", _raise)

    creadas, pendientes, errores = use_case.confirmar_sin_pdf([solicitud])

    assert creadas == []
    assert pendientes == [solicitud]
    assert errores == ["La solicitud pendiente ya no existe."]
