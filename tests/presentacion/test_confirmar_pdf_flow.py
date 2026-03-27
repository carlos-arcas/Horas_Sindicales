from __future__ import annotations

import ast
import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


class _QtConst:
    def __getattr__(self, _name: str) -> int:
        return 0


class _QtDummyModule(types.ModuleType):
    def __getattr__(self, name: str):
        if name == "Qt":
            return _QtConst()
        return type(name, (), {})


def _registrar_stub_pyside() -> None:
    pyside = types.ModuleType("PySide6")
    qt_widgets = _QtDummyModule("PySide6.QtWidgets")
    qt_core = _QtDummyModule("PySide6.QtCore")
    qt_gui = _QtDummyModule("PySide6.QtGui")
    qt_print = _QtDummyModule("PySide6.QtPrintSupport")
    qt_charts = _QtDummyModule("PySide6.QtCharts")
    qt_core.Signal = lambda *args, **kwargs: object()
    qt_core.Slot = lambda *args, **kwargs: (lambda fn: fn)
    pyside.QtWidgets = qt_widgets
    pyside.QtCore = qt_core
    pyside.QtGui = qt_gui
    pyside.QtPrintSupport = qt_print
    pyside.QtCharts = qt_charts
    sys.modules.setdefault("PySide6", pyside)
    sys.modules.setdefault("PySide6.QtWidgets", qt_widgets)
    sys.modules.setdefault("PySide6.QtCore", qt_core)
    sys.modules.setdefault("PySide6.QtGui", qt_gui)
    sys.modules.setdefault("PySide6.QtPrintSupport", qt_print)
    sys.modules.setdefault("PySide6.QtCharts", qt_charts)


_registrar_stub_pyside()

from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.modelos import (
    SolicitudConfirmarPdfResultado,
)
from app.ui.vistas import confirmacion_actions
from app.ui.vistas.confirmacion_orquestacion import (
    ResultadoConfirmacionFlujo,
    on_insertar_sin_pdf,
)

RUTA_ANTERIOR_UI = Path("tests/ui/test_confirmar_pdf_flow.py")
RUTA_ACTUAL_PRESENTACION = Path("tests/presentacion/test_confirmar_pdf_flow.py")


class _FechaHora:
    def __init__(self, value: str) -> None:
        self._value = value

    def toString(self, _fmt: str) -> str:
        return self._value


def _build_window() -> SimpleNamespace:
    solicitud_seleccionada = SolicitudDTO(
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
    solicitud_no_seleccionada = SolicitudDTO(
        id=8,
        persona_id=1,
        fecha_solicitud="2026-01-02",
        fecha_pedida="2026-01-02",
        desde="10:00",
        hasta="11:00",
        completo=False,
        horas=1.0,
        observaciones="",
        pdf_path=None,
        pdf_hash=None,
    )
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
        _pending_solicitudes=[solicitud_seleccionada, solicitud_no_seleccionada],
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
        _selected_pending_solicitudes=lambda: [solicitud_seleccionada],
        _obtener_ids_seleccionados_pendientes=lambda: [7],
        fecha_input=SimpleNamespace(date=lambda: _FechaHora("2026-01-01")),
        desde_input=SimpleNamespace(time=lambda: _FechaHora("09:00")),
        hasta_input=SimpleNamespace(time=lambda: _FechaHora("10:00")),
        toast=SimpleNamespace(warning=Mock()),
        pendientes_table=SimpleNamespace(model=lambda: None),
    )


def _build_window_finalize(eventos: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        abrir_pdf_check=SimpleNamespace(isChecked=lambda: False),
        _procesar_resultado_confirmacion=lambda *_args: eventos.append(
            "insertar_historico"
        ),
        _notify_historico_filter_if_hidden=lambda *_args: eventos.append(
            "notificar_historico"
        ),
        _sync_service=SimpleNamespace(
            register_pdf_log=lambda *_args: eventos.append("registrar_pdf_log")
        ),
        _toast_success=lambda *_args, **_kwargs: eventos.append("toast_ok"),
        _show_pdf_actions_dialog=lambda *_args: eventos.append("dialogo_pdf"),
        _ask_push_after_pdf=lambda: eventos.append("preguntar_sync"),
        _show_confirmation_closure=lambda *_args, **_kwargs: eventos.append(
            "cierre_detalle"
        ),
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


def _llamadas_require_qt(ruta: Path) -> list[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    llamadas: list[str] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if isinstance(nodo.func, ast.Name) and nodo.func.id == "require_qt":
            llamadas.append("require_qt")
    return llamadas


def test_guardrail_confirmar_pdf_flow_ya_no_vive_en_tests_ui() -> None:
    assert not RUTA_ANTERIOR_UI.exists()



def test_guardrail_confirmar_pdf_flow_puro_no_reintroduce_require_qt() -> None:
    assert _llamadas_require_qt(RUTA_ACTUAL_PRESENTACION) == []



def test_click_sin_seleccion_confirma_todas_las_visibles() -> None:
    window = _build_window()
    window._selected_pending_solicitudes = lambda: []
    window._obtener_ids_seleccionados_pendientes = lambda: []

    confirmacion_actions.on_confirmar(window)

    window._execute_confirmar_with_pdf.assert_called_once()
    _persona, selected, pdf_path = window._execute_confirmar_with_pdf.call_args.args
    assert [sol.id for sol in selected] == [7, 8]
    assert pdf_path == "/tmp/salida.pdf"
    window.toast.warning.assert_not_called()



def test_click_con_seleccion_llama_use_case_con_argumentos() -> None:
    window = _build_window()

    confirmacion_actions.on_confirmar(window)

    window._execute_confirmar_with_pdf.assert_called_once()
    _persona, selected, pdf_path = window._execute_confirmar_with_pdf.call_args.args
    assert [sol.id for sol in selected] == [7]
    assert pdf_path == "/tmp/salida.pdf"
    window._toast_success.assert_not_called()



def test_click_con_seleccion_parcial_no_confirma_todos_los_visibles(caplog) -> None:
    window = _build_window()

    with caplog.at_level(logging.INFO):
        confirmacion_actions.on_confirmar(window)

    _persona, selected, _pdf_path = window._execute_confirmar_with_pdf.call_args.args
    assert [sol.id for sol in selected] == [7]
    registro_start = next(
        registro
        for registro in caplog.records
        if registro.getMessage() == "UI_CONFIRMAR_PDF_START"
    )
    assert registro_start.selected_ids == [7]
    assert registro_start.selected_count == 1
    assert registro_start.pendientes_count == 0



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



def test_finalize_confirmar_with_pdf_respeta_orden_historico_pdf_y_sync(
    monkeypatch,
) -> None:
    eventos: list[str] = []
    window = _build_window_finalize(eventos)
    persona = SimpleNamespace(id=1)
    ruta_pdf = Path("/tmp/salida.pdf")
    monkeypatch.setattr(
        confirmacion_actions,
        "abrir_archivo_local",
        lambda *_args: eventos.append("abrir_pdf"),
    )
    monkeypatch.setattr(Path, "exists", lambda self: self == ruta_pdf)

    exito_visible = confirmacion_actions.finalize_confirmar_with_pdf(
        window,
        persona,
        "corr-1",
        ruta_pdf,
        [_build_solicitud_confirmada()],
        [7],
        [],
        [],
    )

    assert exito_visible is True
    assert eventos == [
        "insertar_historico",
        "notificar_historico",
        "registrar_pdf_log",
        "toast_ok",
        "dialogo_pdf",
        "preguntar_sync",
    ]



def test_finalize_confirmar_with_pdf_si_register_pdf_log_falla_mantiene_exito_y_loguea(
    caplog, monkeypatch
) -> None:
    eventos: list[str] = []

    def _fallar_register_pdf_log(*_args) -> None:
        raise RuntimeError("db rota")

    window = _build_window_finalize(eventos)
    window._sync_service = SimpleNamespace(register_pdf_log=_fallar_register_pdf_log)
    persona = SimpleNamespace(id=1)
    ruta_pdf = Path("/tmp/salida.pdf")
    monkeypatch.setattr(Path, "exists", lambda self: self == ruta_pdf)

    with caplog.at_level(logging.ERROR):
        exito_visible = confirmacion_actions.finalize_confirmar_with_pdf(
            window,
            persona,
            "corr-1",
            ruta_pdf,
            [_build_solicitud_confirmada()],
            [7],
            [],
            [],
        )

    assert exito_visible is True
    assert eventos == [
        "insertar_historico",
        "notificar_historico",
        "toast_ok",
        "dialogo_pdf",
        "preguntar_sync",
    ]
    assert any(
        registro.getMessage() == "ui.confirmacion.register_pdf_log_failed"
        for registro in caplog.records
    )
    registro_error = next(
        registro
        for registro in caplog.records
        if registro.getMessage() == "ui.confirmacion.register_pdf_log_failed"
    )
    assert registro_error.levelno == logging.ERROR
    assert registro_error.extra == {
        "operation": "confirmar_y_generar_pdf",
        "persona_id": 1,
        "fechas_count": 1,
        "correlation_id": "corr-1",
    }



def test_finalize_confirmar_with_pdf_con_error_no_pide_sync_y_muestra_cierre() -> None:
    eventos: list[str] = []
    window = _build_window_finalize(eventos)
    persona = SimpleNamespace(id=1)

    exito_visible = confirmacion_actions.finalize_confirmar_with_pdf(
        window,
        persona,
        "corr-1",
        None,
        [_build_solicitud_confirmada()],
        [],
        ["error_pdf"],
        [],
    )

    assert exito_visible is False
    assert "preguntar_sync" not in eventos
    assert "cierre_detalle" in eventos



def test_finalize_confirmar_with_pdf_descarta_exito_si_pdf_no_existe(
    caplog, monkeypatch
) -> None:
    eventos: list[str] = []
    window = _build_window_finalize(eventos)
    persona = SimpleNamespace(id=1)
    ruta_pdf = Path("/tmp/inexistente.pdf")
    monkeypatch.setattr(Path, "exists", lambda self: False)

    with caplog.at_level(logging.WARNING):
        exito_visible = confirmacion_actions.finalize_confirmar_with_pdf(
            window,
            persona,
            "corr-1",
            ruta_pdf,
            [_build_solicitud_confirmada()],
            [7],
            [],
            [],
        )

    assert exito_visible is False
    assert eventos == [
        "insertar_historico",
        "notificar_historico",
    ]
    registro_warning = next(
        registro
        for registro in caplog.records
        if registro.getMessage() == "UI_CONFIRMAR_TOAST_SUCCESS_DESCARTADO"
    )
    assert registro_warning.motivo == "pdf_inexistente_en_disco"
    assert registro_warning.pdf_path == str(ruta_pdf)
    assert registro_warning.creadas_count == 1
    assert registro_warning.errores_count == 0
    assert registro_warning.confirmadas_ids_count == 1
    assert registro_warning.correlation_id == "corr-1"
    assert registro_warning.persona_id == 1



def test_apply_finalize_no_loguea_ok_visible_si_pdf_no_existe(caplog) -> None:
    finalize_calls: list[tuple[object, ...]] = []
    window = _build_window()
    persona = SimpleNamespace(id=1)
    outcome = ResultadoConfirmacionFlujo(
        correlation_id="corr-1",
        resultado=SolicitudConfirmarPdfResultado(
            estado="OK_CON_PDF",
            confirmadas=1,
            confirmadas_ids=[7],
            errores=[],
            pdf_generado=Path("/tmp/inexistente.pdf"),
            sync_permitido=True,
            pendientes_restantes=[],
        ),
        creadas=[_build_solicitud_confirmada()],
        pendientes_restantes=[],
    )

    def _finalize(*args):
        finalize_calls.append(args)
        return False

    window._finalize_confirmar_with_pdf = _finalize

    with caplog.at_level(logging.INFO):
        from app.ui.vistas import confirmacion_adaptador_qt

        confirmacion_adaptador_qt.apply_finalize(window, persona, outcome)

    assert len(finalize_calls) == 1
    registro_ok = next(
        registro
        for registro in caplog.records
        if registro.getMessage() == "UI_CONFIRMAR_PDF_OK"
    )
    assert registro_ok.exito_visible is False



def test_build_confirmation_payload_no_expone_accion_sync() -> None:
    window = SimpleNamespace(
        _personas=[SimpleNamespace(id=1, nombre="Ana")],
        saldos_card=SimpleNamespace(saldo_periodo_restante_text=lambda: "10:00"),
        _focus_historico_search=lambda: None,
        _on_push_now=lambda: None,
        main_tabs=SimpleNamespace(setCurrentIndex=lambda _index: None),
        _undo_confirmation=lambda _ids: None,
    )

    payload = confirmacion_actions.build_confirmation_payload(
        window,
        [_build_solicitud_confirmada()],
        [],
        correlation_id="corr-1",
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



def test_insertar_sin_pdf_con_seleccion_parcial_confirma_solo_la_seleccion() -> None:
    window = _build_window()
    controller = SimpleNamespace(
        confirmar_lote=Mock(
            return_value=([7], [], None, window._selected_pending_solicitudes(), [])
        )
    )
    window._solicitudes_controller = controller
    window._procesar_resultado_confirmacion = Mock()
    window._show_confirmation_closure = Mock()
    window._notify_historico_filter_if_hidden = Mock()

    on_insertar_sin_pdf(window)

    controller.confirmar_lote.assert_called_once()
    selected = controller.confirmar_lote.call_args.args[0]
    assert [sol.id for sol in selected] == [7]



def test_insertar_sin_pdf_sin_seleccion_no_ejecuta_caso_de_uso() -> None:
    window = _build_window()
    window._selected_pending_solicitudes = lambda: []
    window._selected_pending_row_indexes = lambda: []
    window._solicitudes_controller = SimpleNamespace(confirmar_lote=Mock())

    on_insertar_sin_pdf(window)

    window._solicitudes_controller.confirmar_lote.assert_not_called()
    window.toast.warning.assert_called_once()



def test_insertar_sin_pdf_con_todas_las_visibles_seleccionadas_mantiene_no_regresion() -> None:
    window = _build_window()
    todas = list(window._pending_solicitudes)
    window._selected_pending_solicitudes = lambda: todas
    window._selected_pending_row_indexes = lambda: [0, 1]
    controller = SimpleNamespace(
        confirmar_lote=Mock(return_value=([7, 8], [], None, todas, []))
    )
    window._solicitudes_controller = controller
    window._procesar_resultado_confirmacion = Mock()
    window._show_confirmation_closure = Mock()
    window._notify_historico_filter_if_hidden = Mock()

    on_insertar_sin_pdf(window)

    selected = controller.confirmar_lote.call_args.args[0]
    assert [sol.id for sol in selected] == [7, 8]
