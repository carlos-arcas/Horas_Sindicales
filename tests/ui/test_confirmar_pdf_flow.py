from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from tests.ui.conftest import require_qt

require_qt()

from app.application.dto import SolicitudDTO
from app.ui.vistas import confirmacion_actions


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
        _execute_confirmar_with_pdf=Mock(return_value=("corr-1", Path("/tmp/salida.pdf"), [], [7], [], [])),
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
    window._toast_success.assert_called_once()


def test_error_del_use_case_muestra_toast_error_y_rehabilita_ui() -> None:
    window = _build_window()

    def _raise(_persona, _selected, _pdf_path):
        raise RuntimeError("boom")

    window._execute_confirmar_with_pdf = Mock(side_effect=_raise)

    confirmacion_actions.on_confirmar(window)

    window._toast_error.assert_called_once()
    window._set_processing_state.assert_called_with(False)
