from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from tests.ui.conftest import require_qt

require_qt()

from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.modelos import SolicitudConfirmarPdfResultado
from app.ui.vistas import confirmacion_actions
from app.ui.vistas.confirmacion_orquestacion import ResultadoConfirmacionFlujo


class _FechaHora:
    def __init__(self, value: str) -> None:
        self._value = value

    def toString(self, _fmt: str) -> str:
        return self._value


def _build_window() -> SimpleNamespace:
    return SimpleNamespace(
        _ui_ready=True,
        _pending_view_all=False,
        _pending_conflict_rows=set(),
        _run_preconfirm_checks=lambda: True,
        _current_persona=lambda: SimpleNamespace(id=1),
        _selected_pending_for_editing=lambda: None,
        _dump_estado_pendientes=lambda _motivo: None,
        _selected_pending_row_indexes=lambda: [0],
        _set_processing_state=Mock(),
        _finalize_confirmar_with_pdf=Mock(),
        _toast_error=Mock(),
        _toast_success=Mock(),
        _prompt_confirm_pdf_path=lambda _selected: "/tmp/salida.pdf",
        _last_selected_pdf_path=None,
        _execute_confirmar_with_pdf=Mock(
            return_value=ResultadoConfirmacionFlujo(
                correlation_id="corr-1",
                resultado=SolicitudConfirmarPdfResultado(
                    estado="OK_CON_PDF",
                    confirmadas=1,
                    confirmadas_ids=[7],
                    errores=[],
                    pdf_generado=Path("/tmp/salida.pdf"),
                    sync_permitido=True,
                    pendientes_restantes=[],
                ),
                creadas=[],
                pendientes_restantes=[],
            )
        ),
        _selected_pending_solicitudes=lambda: [
            SolicitudDTO(
                id=7,
                persona_id=1,
                fecha_solicitud="2026-01-01",
                fecha_pedida="2026-01-01",
                desde="09:00",
                hasta="10:00",
                completo=False,
                horas=1.0,
                observaciones="",
                pdf_path=None,
                pdf_hash=None,
            )
        ],
        _obtener_ids_seleccionados_pendientes=lambda: [7],
        fecha_input=SimpleNamespace(date=lambda: _FechaHora("2026-01-01")),
        desde_input=SimpleNamespace(time=lambda: _FechaHora("09:00")),
        hasta_input=SimpleNamespace(time=lambda: _FechaHora("10:00")),
        toast=SimpleNamespace(warning=Mock()),
        pendientes_table=SimpleNamespace(model=lambda: None),
    )


def test_click_sin_seleccion_no_llama_use_case() -> None:
    window = _build_window()
    window._selected_pending_solicitudes = lambda: []
    window._obtener_ids_seleccionados_pendientes = lambda: []

    confirmacion_actions.on_confirmar(window)

    window._execute_confirmar_with_pdf.assert_not_called()
    window.toast.warning.assert_called_once()


def test_click_con_seleccion_llama_use_case_con_argumentos() -> None:
    window = _build_window()

    confirmacion_actions.on_confirmar(window)

    window._execute_confirmar_with_pdf.assert_called_once()
    _persona, selected, pdf_path = window._execute_confirmar_with_pdf.call_args.args
    assert [sol.id for sol in selected] == [7]
    assert pdf_path == "/tmp/salida.pdf"
    window._toast_success.assert_not_called()


def test_click_con_pdf_existente_muestra_toast_success(monkeypatch) -> None:
    window = _build_window()
    ruta = Path("/tmp/salida.pdf")

    monkeypatch.setattr(Path, "exists", lambda self: self == ruta)

    confirmacion_actions.on_confirmar(window)

    window._finalize_confirmar_with_pdf.assert_called_once()
    window._toast_success.assert_not_called()


def test_error_del_use_case_muestra_toast_error_y_rehabilita_ui() -> None:
    window = _build_window()

    def _raise(_persona, _selected, _pdf_path):
        raise RuntimeError("boom")

    window._execute_confirmar_with_pdf = Mock(side_effect=_raise)

    confirmacion_actions.on_confirmar(window)

    window._toast_error.assert_called_once()
    window._set_processing_state.assert_called_with(False)



def _build_window_finalize(eventos: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        abrir_pdf_check=SimpleNamespace(isChecked=lambda: False),
        _procesar_resultado_confirmacion=lambda *_args: eventos.append("insertar_historico"),
        _notify_historico_filter_if_hidden=lambda *_args: eventos.append("notificar_historico"),
        _sync_service=SimpleNamespace(register_pdf_log=lambda *_args: eventos.append("registrar_pdf_log")),
        _toast_success=lambda *_args, **_kwargs: eventos.append("toast_ok"),
        _show_pdf_actions_dialog=lambda *_args: eventos.append("dialogo_pdf"),
        _ask_push_after_pdf=lambda: eventos.append("preguntar_sync"),
        _show_confirmation_closure=lambda *_args, **_kwargs: eventos.append("cierre_detalle"),
    )


def _build_solicitud_confirmada() -> SolicitudDTO:
    return SolicitudDTO(
        id=7,
        persona_id=1,
        fecha_solicitud="2026-01-01",
        fecha_pedida="2026-01-01",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="",
        pdf_path="/tmp/salida.pdf",
        pdf_hash="hash-1",
    )


def test_finalize_confirmar_with_pdf_respeta_orden_historico_pdf_y_sync(monkeypatch) -> None:
    eventos: list[str] = []
    window = _build_window_finalize(eventos)
    persona = SimpleNamespace(id=1)
    ruta_pdf = Path('/tmp/salida.pdf')
    monkeypatch.setattr(confirmacion_actions, 'abrir_archivo_local', lambda *_args: eventos.append('abrir_pdf'))
    monkeypatch.setattr(Path, 'exists', lambda self: self == ruta_pdf)

    confirmacion_actions.finalize_confirmar_with_pdf(
        window,
        persona,
        'corr-1',
        ruta_pdf,
        [_build_solicitud_confirmada()],
        [7],
        [],
        [],
    )

    assert eventos == [
        'insertar_historico',
        'notificar_historico',
        'registrar_pdf_log',
        'toast_ok',
        'dialogo_pdf',
        'preguntar_sync',
    ]


def test_finalize_confirmar_with_pdf_con_error_no_pide_sync_y_muestra_cierre() -> None:
    eventos: list[str] = []
    window = _build_window_finalize(eventos)
    persona = SimpleNamespace(id=1)

    confirmacion_actions.finalize_confirmar_with_pdf(
        window,
        persona,
        'corr-1',
        None,
        [_build_solicitud_confirmada()],
        [],
        ['error_pdf'],
        [],
    )

    assert 'preguntar_sync' not in eventos
    assert 'cierre_detalle' in eventos


def test_build_confirmation_payload_no_expone_accion_sync() -> None:
    window = SimpleNamespace(
        _personas=[SimpleNamespace(id=1, nombre='Ana')],
        saldos_card=SimpleNamespace(saldo_periodo_restante_text=lambda: '10:00'),
        _focus_historico_search=lambda: None,
        _on_push_now=lambda: None,
        main_tabs=SimpleNamespace(setCurrentIndex=lambda _index: None),
        _undo_confirmation=lambda _ids: None,
    )

    payload = confirmacion_actions.build_confirmation_payload(
        window,
        [_build_solicitud_confirmada()],
        [],
        correlation_id='corr-1',
    )

    assert payload.on_sync_now is None


def test_on_confirmar_respeta_flujo_historico_pdf_sync() -> None:
    eventos: list[str] = []
    solicitud = _build_solicitud_confirmada()

    def _execute(_persona, _selected, _pdf_path):
        eventos.append("insertar_historico")
        eventos.append("generar_pdf")
        return ResultadoConfirmacionFlujo(
            correlation_id="corr-1",
            resultado=SolicitudConfirmarPdfResultado(
                estado="OK_CON_PDF",
                confirmadas=1,
                confirmadas_ids=[7],
                errores=[],
                pdf_generado=Path("/tmp/salida.pdf"),
                sync_permitido=True,
                pendientes_restantes=[],
            ),
            creadas=[solicitud],
            pendientes_restantes=[],
        )

    window = _build_window()
    window._execute_confirmar_with_pdf = Mock(side_effect=_execute)
    window._finalize_confirmar_with_pdf = Mock(
        side_effect=lambda *_args: eventos.append("pedir_sync")
    )

    confirmacion_actions.on_confirmar(window)

    assert eventos == ["insertar_historico", "generar_pdf", "pedir_sync"]


def test_on_confirmar_error_pdf_no_pide_sync_y_no_muestra_cierre_tecnico() -> None:
    window = _build_window()
    window._execute_confirmar_with_pdf = Mock(side_effect=RuntimeError("error_pdf"))
    window._ask_push_after_pdf = Mock()
    window._show_confirmation_closure = Mock()

    confirmacion_actions.on_confirmar(window)

    window._ask_push_after_pdf.assert_not_called()
    window._show_confirmation_closure.assert_not_called()
    window._finalize_confirmar_with_pdf.assert_not_called()
    window._toast_error.assert_called_once()
