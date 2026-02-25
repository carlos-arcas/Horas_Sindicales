from types import SimpleNamespace
from dataclasses import replace

import logging
import uuid
from unittest.mock import Mock

from app.application.dto import ResultadoCrearSolicitudDTO, SolicitudDTO
from app.ui.controllers.pdf_controller import PdfController
from app.ui.controllers.personas_controller import PersonasController
from app.ui.controllers.solicitudes_controller import SolicitudesController
from app.ui.controllers.sync_controller import SyncController


def _build_window_for_solicitudes(solicitud: SolicitudDTO | None) -> SimpleNamespace:
    use_cases = Mock()
    use_cases.calcular_minutos_solicitud.return_value = 60
    use_cases.minutes_to_hours_float.return_value = 1.0
    use_cases.buscar_duplicado.return_value = None
    creada = replace(solicitud, id=55) if solicitud else None
    use_cases.crear_resultado.return_value = ResultadoCrearSolicitudDTO(
        success=True,
        warnings=[],
        errores=[],
        entidad=creada,
        saldos=None,
    )
    return SimpleNamespace(
        _build_preview_solicitud=Mock(return_value=solicitud),
        _solicitud_use_cases=use_cases,
        _resolve_backend_conflict=Mock(return_value=True),
        _reload_pending_views=Mock(),
        _refresh_historico=Mock(),
        _refresh_saldos=Mock(),
        _update_action_state=Mock(),
        _handle_duplicate_detected=Mock(return_value=False),
        _undo_last_added_pending=Mock(),
        notas_input=SimpleNamespace(toPlainText=Mock(return_value=""), setPlainText=Mock()),
        notifications=Mock(),
        toast=Mock(),
        desde_input=SimpleNamespace(setFocus=Mock()),
        _show_critical_error=Mock(),
        _set_processing_state=Mock(),
    )


def test_personas_controller_calls_crear() -> None:
    use_cases = Mock()
    use_cases.crear.return_value = SimpleNamespace(id=7)
    window = SimpleNamespace(_persona_use_cases=use_cases, _load_personas=Mock(), toast=Mock())

    controller = PersonasController(window)
    controller.on_add_persona(SimpleNamespace(nombre="X"))

    use_cases.crear.assert_called_once()
    window._load_personas.assert_called_once_with(select_id=7)


def test_solicitudes_controller_calls_agregar() -> None:
    solicitud = SolicitudDTO(
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
    window = _build_window_for_solicitudes(solicitud)

    controller = SolicitudesController(window)
    controller.on_add_pendiente()

    window._solicitud_use_cases.crear_resultado.assert_called_once()


def test_solicitudes_controller_no_permite_anadir_sin_delegada() -> None:
    window = _build_window_for_solicitudes(None)

    controller = SolicitudesController(window)
    controller.on_add_pendiente()

    window.notifications.notify_validation_error.assert_called_once()
    window._solicitud_use_cases.crear_resultado.assert_not_called()


def test_solicitudes_controller_duplicate_guides_to_existing() -> None:
    solicitud = SolicitudDTO(
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
    window = _build_window_for_solicitudes(solicitud)
    window._solicitud_use_cases.buscar_duplicado.return_value = replace(solicitud, id=3, generated=False)
    window._handle_duplicate_detected.return_value = False

    controller = SolicitudesController(window)
    controller.on_add_pendiente()

    window._handle_duplicate_detected.assert_called_once()
    window._solicitud_use_cases.crear_resultado.assert_not_called()




def test_solicitudes_controller_muestra_warning_no_bloqueante() -> None:
    solicitud = SolicitudDTO(
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
    window = _build_window_for_solicitudes(solicitud)
    window._solicitud_use_cases.crear_resultado.return_value = ResultadoCrearSolicitudDTO(
        success=True,
        warnings=["Saldo insuficiente. La petición se ha registrado igualmente."],
        errores=[],
        entidad=replace(solicitud, id=77),
        saldos=None,
    )

    controller = SolicitudesController(window)
    controller.on_add_pendiente()

    window.toast.info.assert_called_once()
    window._reload_pending_views.assert_called_once()

def test_sync_controller_updates_button_state() -> None:
    window = SimpleNamespace(
        _sync_service=SimpleNamespace(is_configured=Mock(return_value=True)),
        _sync_in_progress=False,
        sync_button=SimpleNamespace(setEnabled=Mock()),
        review_conflicts_button=SimpleNamespace(setEnabled=Mock(), setText=Mock()),
        _conflicts_service=SimpleNamespace(count_conflicts=Mock(return_value=0)),
    )
    controller = SyncController(window)

    controller.update_sync_button_state()

    window.sync_button.setEnabled.assert_called_once_with(True)
    window.review_conflicts_button.setText.assert_called_once()


def test_sync_controller_blocks_reentrancy() -> None:
    window = SimpleNamespace(
        _sync_service=SimpleNamespace(is_configured=Mock(return_value=True)),
        _sync_in_progress=True,
        _set_sync_in_progress=Mock(),
        _on_sync_finished=Mock(),
        _on_sync_failed=Mock(),
    )

    controller = SyncController(window)
    controller.on_sync()

    window._set_sync_in_progress.assert_not_called()


def test_sync_controller_marks_config_incomplete() -> None:
    window = SimpleNamespace(
        _sync_service=SimpleNamespace(is_configured=Mock(return_value=False)),
        _sync_in_progress=False,
        _set_config_incomplete_state=Mock(),
        toast=Mock(),
    )

    controller = SyncController(window)
    controller.on_sync()

    window._set_config_incomplete_state.assert_called_once()


def test_pdf_controller_delegates_name_generation() -> None:
    use_cases = Mock()
    use_cases.sugerir_nombre_pdf_historico.return_value = "hist.pdf"

    controller = PdfController(use_cases)

    assert controller.sugerir_nombre_historico(SimpleNamespace()) == "hist.pdf"
    use_cases.sugerir_nombre_pdf_historico.assert_called_once()


def test_solicitudes_controller_logs_correlation_id(caplog) -> None:
    solicitud = SolicitudDTO(
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
    window = _build_window_for_solicitudes(solicitud)

    controller = SolicitudesController(window)
    with caplog.at_level(logging.INFO):
        controller.on_add_pendiente()

    assert window._solicitud_use_cases.crear_resultado.called
    kwargs = window._solicitud_use_cases.crear_resultado.call_args.kwargs
    correlation_id = kwargs["correlation_id"]
    uuid.UUID(correlation_id)

    mensajes = [record.getMessage() for record in caplog.records]
    assert any("agregar_pendiente_started" in mensaje for mensaje in mensajes)
    assert any("agregar_pendiente_succeeded" in mensaje for mensaje in mensajes)
