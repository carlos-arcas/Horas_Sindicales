from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.headless_safe

from app.application.dto import ResultadoCrearSolicitudDTO, SolicitudDTO
from app.domain.services import BusinessRuleError
from app.ui.controllers.solicitudes_controller import SolicitudesController


def _solicitud_base() -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=1,
        fecha_solicitud="2024-01-01",
        fecha_pedida="2024-01-01",
        desde="10:00",
        hasta="11:00",
        completo=False,
        horas=0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )


def _build_window_for_add(solicitud: SolicitudDTO | None) -> SimpleNamespace:
    use_cases = Mock()
    use_cases.buscar_duplicado.return_value = None
    use_cases.calcular_minutos_solicitud.return_value = 90
    use_cases.minutes_to_hours_float.return_value = 1.5
    use_cases.crear_resultado.return_value = ResultadoCrearSolicitudDTO(
        success=True,
        warnings=[],
        errores=[],
        entidad=replace(solicitud, id=10) if solicitud else None,
        saldos=None,
    )

    return SimpleNamespace(
        _build_preview_solicitud=Mock(return_value=solicitud),
        _selected_pending_for_editing=Mock(return_value=None),
        _solicitud_use_cases=use_cases,
        _handle_duplicate_detected=Mock(return_value=False),
        _resolve_backend_conflict=Mock(return_value=True),
        _set_processing_state=Mock(),
        _reload_pending_views=Mock(),
        _refresh_historico=Mock(),
        _refresh_saldos=Mock(),
        _update_action_state=Mock(),
        _undo_last_added_pending=Mock(),
        _show_critical_error=Mock(),
        notas_input=SimpleNamespace(toPlainText=Mock(return_value="nota"), setPlainText=Mock()),
        desde_input=SimpleNamespace(setFocus=Mock()),
        notifications=Mock(),
        toast=Mock(),
    )


def test_on_add_pendiente_success() -> None:
    solicitud = _solicitud_base()
    window = _build_window_for_add(solicitud)

    controller = SolicitudesController(window)
    controller.on_add_pendiente()

    window._solicitud_use_cases.crear_resultado.assert_called_once()
    window.notifications.notify_added_pending.assert_called_once()
    window._refresh_historico.assert_called_once()


def test_on_add_pendiente_validation_fail() -> None:
    window = _build_window_for_add(None)

    controller = SolicitudesController(window)
    controller.on_add_pendiente()

    window.notifications.notify_validation_error.assert_called_once()
    window._solicitud_use_cases.crear_resultado.assert_not_called()


def test_confirmar_lote_success_generar_pdf() -> None:
    solicitud = replace(_solicitud_base(), id=5)
    window = SimpleNamespace(
        _solicitud_use_cases=SimpleNamespace(
            confirmar_y_generar_pdf_por_filtro=Mock(return_value=(Path("/tmp/out.pdf"), [5], "ok"))
        )
    )
    controller = SolicitudesController(window)

    confirmadas_ids, errores, ruta, confirmadas, pendientes_restantes = controller.confirmar_lote(
        [solicitud],
        correlation_id="corr-1",
        generar_pdf=True,
        pdf_path="/tmp/out.pdf",
        filtro_delegada=1,
    )

    assert confirmadas_ids == [5]
    assert errores == []
    assert ruta == Path("/tmp/out.pdf")
    assert confirmadas == [solicitud]
    assert pendientes_restantes == []


def test_confirmar_lote_business_rule_error_colision_ruta() -> None:
    solicitud = replace(_solicitud_base(), id=8)
    window = SimpleNamespace(
        _solicitud_use_cases=SimpleNamespace(
            confirmar_y_generar_pdf_por_filtro=Mock(side_effect=BusinessRuleError("Colisión de ruta PDF"))
        )
    )
    controller = SolicitudesController(window)

    with pytest.raises(BusinessRuleError, match="Colisión de ruta"):
        controller.confirmar_lote(
            [solicitud],
            correlation_id="corr-2",
            generar_pdf=True,
            pdf_path="/tmp/out.pdf",
            filtro_delegada=1,
        )
