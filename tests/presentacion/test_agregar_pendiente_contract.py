from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

from app.application.dto import ResultadoCrearSolicitudDTO, SolicitudDTO
from app.ui.controllers.solicitudes_controller import SolicitudesController


def _solicitud_valida() -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=7,
        fecha_solicitud="2026-03-01",
        fecha_pedida="2026-03-05",
        desde="09:00",
        hasta="10:30",
        completo=False,
        horas=0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )


def _ventana_fake(solicitud: SolicitudDTO | None) -> SimpleNamespace:
    use_cases = Mock()
    use_cases.buscar_conflicto_pendiente.return_value = None
    use_cases.calcular_minutos_solicitud.return_value = 90
    use_cases.minutes_to_hours_float.return_value = 1.5
    use_cases.crear_resultado.return_value = ResultadoCrearSolicitudDTO(
        success=True,
        warnings=[],
        errores=[],
        entidad=replace(solicitud, id=123) if solicitud else None,
        saldos=None,
    )

    return SimpleNamespace(
        _build_preview_solicitud=Mock(return_value=solicitud),
        _selected_pending_for_editing=Mock(return_value=None),
        _solicitud_use_cases=use_cases,
        _handle_duplicate_detected=Mock(return_value=False),
        ir_a_pendiente_existente=Mock(),
        _resolve_backend_conflict=Mock(return_value=True),
        _set_processing_state=Mock(),
        _reload_pending_views=Mock(),
        _update_pending_totals=Mock(),
        _refresh_historico=Mock(),
        _refresh_saldos=Mock(),
        _update_action_state=Mock(),
        _refrescar_estado_operativa=Mock(),
        _update_global_context=Mock(),
        _undo_last_added_pending=Mock(),
        _show_critical_error=Mock(),
        notas_input=SimpleNamespace(toPlainText=Mock(return_value="nota contrato"), setPlainText=Mock()),
        desde_input=SimpleNamespace(setFocus=Mock()),
        notifications=SimpleNamespace(
            notify_validation_error=Mock(),
            notify_added_pending=Mock(),
        ),
        toast=SimpleNamespace(warning=Mock(), info=Mock()),
    )


def test_agregar_pendiente_contrato_refresca_cajon_totales_saldo_y_estado() -> None:
    solicitud = _solicitud_valida()
    ventana = _ventana_fake(solicitud)
    controller = SolicitudesController(ventana)

    controller.on_add_pendiente()

    ventana._solicitud_use_cases.crear_resultado.assert_called_once()
    ventana._reload_pending_views.assert_called_once()
    ventana._update_pending_totals.assert_called_once()
    ventana._refresh_saldos.assert_not_called()
    ventana._refrescar_estado_operativa.assert_called_once_with("pendiente_added")
    ventana._update_global_context.assert_called_once()
    ventana.notifications.notify_added_pending.assert_called_once()
    ventana.notifications.notify_validation_error.assert_not_called()
    ventana.toast.warning.assert_not_called()


def test_agregar_pendiente_con_datos_invalidos_no_inserta_y_notifica_controlado() -> None:
    ventana = _ventana_fake(None)
    controller = SolicitudesController(ventana)

    controller.on_add_pendiente()

    ventana._solicitud_use_cases.crear_resultado.assert_not_called()
    ventana._reload_pending_views.assert_not_called()
    ventana._update_pending_totals.assert_not_called()
    ventana._refresh_saldos.assert_not_called()
    ventana._refrescar_estado_operativa.assert_not_called()
    ventana._update_action_state.assert_not_called()
    ventana.notifications.notify_validation_error.assert_called_once()
    ventana.toast.warning.assert_not_called()
