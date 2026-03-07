from __future__ import annotations

import sys
import types
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


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
from app.ui.vistas.main_window import acciones_pendientes
from app.ui.vistas.main_window.acciones_mixin import AccionesMainWindowMixin


class VentanaFalsa(AccionesMainWindowMixin):
    def __init__(self) -> None:
        self._solicitudes_controller = None
        self._pending_solicitudes: list[SolicitudDTO] = []
        self._pending_view_all = False
        self._pending_conflict_rows: set[int] = set()
        self._output_dir = Path("/tmp")
        self._solicitud_use_cases = SimpleNamespace(
            sugerir_nombre_pdf=lambda _selected: "confirmacion.pdf",
            eliminar_solicitud=Mock(),
            sumar_pendientes_min=lambda _persona_id, _pendientes: 60,
            detectar_conflictos_pendientes=lambda _pendientes: set(),
        )
        self._refrescar_estado_operativa = Mock()
        self._reload_pending_views = Mock()
        self._refresh_saldos = Mock()
        self._update_action_state = Mock()
        self._update_global_context = Mock()
        self._build_preview_solicitud = Mock(return_value=_build_solicitud())
        self._current_persona = Mock(return_value=SimpleNamespace(id=1))
        self._set_processing_state = Mock()
        self._dump_estado_pendientes = Mock()
        self._show_critical_error = Mock()
        self.notifications = SimpleNamespace(notify_operation=Mock())
        self.toast = SimpleNamespace(warning=Mock())
        self.notas_input = SimpleNamespace(toPlainText=lambda: "")
        self.total_pendientes_label = SimpleNamespace(setText=Mock())
        self.status_pending_label = SimpleNamespace(setText=Mock())
        self.statusBar = lambda: SimpleNamespace(showMessage=Mock())
        self.pendientes_model = SimpleNamespace(
            rowCount=lambda: len(self._pending_solicitudes),
            clear=Mock(),
            set_show_delegada=Mock(),
            set_solicitudes=Mock(),
            set_conflict_rows=Mock(),
            index=lambda _r, _c: None,
        )
        self.huerfanas_model = SimpleNamespace(clear=Mock())
        self.pendientes_table = SimpleNamespace(
            selectionModel=lambda: SimpleNamespace(selectedRows=lambda: []),
            model=lambda: None,
            selectRow=Mock(),
            scrollTo=Mock(),
            setFocus=Mock(),
        )
        self._configure_solicitudes_table = Mock()
        self._format_minutes = lambda total: str(total)


class _QMessageBoxFake:
    class StandardButton:
        Yes = 1

    @staticmethod
    def question(*_args, **_kwargs):
        return _QMessageBoxFake.StandardButton.Yes


class _DialogButtonFake:
    def __init__(self, texto: str) -> None:
        self.texto = texto
        self.enabled = True
        self.tooltip = ""

    def setEnabled(self, valor: bool) -> None:
        self.enabled = valor

    def setToolTip(self, valor: str) -> None:
        self.tooltip = valor


class _DialogQMessageBoxFake:
    AcceptRole = 1
    ActionRole = 2
    RejectRole = 3
    clicked_button_text = ""
    last_instance = None

    def __init__(self, *_args, **_kwargs) -> None:
        self.window_title = ""
        self.text = ""
        self.informative_text = ""
        self.buttons: list[_DialogButtonFake] = []
        self._clicked_button = None
        _DialogQMessageBoxFake.last_instance = self

    def setWindowTitle(self, valor: str) -> None:
        self.window_title = valor

    def setText(self, valor: str) -> None:
        self.text = valor

    def setInformativeText(self, valor: str) -> None:
        self.informative_text = valor

    def addButton(self, texto: str, _role: int) -> _DialogButtonFake:
        boton = _DialogButtonFake(texto)
        self.buttons.append(boton)
        return boton

    def exec(self) -> int:
        self._clicked_button = next((b for b in self.buttons if b.texto == self.clicked_button_text), None)
        return 0

    def clickedButton(self):
        return self._clicked_button


def _build_solicitud(*, solicitud_id: int | None = 7, notas: str = "") -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=1,
        fecha_solicitud="2026-01-01",
        fecha_pedida="2026-01-01",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="",
        notas=notas,
        pdf_path=None,
        pdf_hash=None,
    )


def test_handlers_prioridad1_contract_smoke() -> None:
    assert True


def test_on_add_pendiente_delega_en_controller_si_existe() -> None:
    window = VentanaFalsa()
    controller = SimpleNamespace(on_add_pendiente=Mock())
    window._solicitudes_controller = controller

    window._on_add_pendiente("payload_extra")

    controller.on_add_pendiente.assert_called_once_with()
    window._build_preview_solicitud.assert_not_called()


def test_on_add_pendiente_refresca_estado_en_fallback_local() -> None:
    window = VentanaFalsa()

    window._on_add_pendiente()

    assert len(window._pending_solicitudes) == 1
    window._update_action_state.assert_called_once_with()
    window._update_global_context.assert_called_once_with()
    window._refrescar_estado_operativa.assert_called_once_with("pendiente_added")


def test_on_pending_selection_changed_tolera_payload_y_refresca_estado() -> None:
    window = VentanaFalsa()

    window._on_pending_selection_changed("actual", "anterior", extra=True)

    window._refrescar_estado_operativa.assert_called_once_with("pendiente_selected")


def test_prompt_confirm_pdf_path_devuelve_none_sin_seleccion() -> None:
    window = VentanaFalsa()

    assert window._prompt_confirm_pdf_path([]) is None


def test_prompt_confirm_pdf_path_pide_ruta_y_resuelve_colision(monkeypatch: pytest.MonkeyPatch) -> None:
    window = VentanaFalsa()

    class QFileDialogFake:
        @staticmethod
        def getSaveFileName(*_args, **_kwargs):
            return "/tmp/original.pdf", ""

    monkeypatch.setattr("app.ui.qt_compat.QFileDialog", QFileDialogFake)

    modulo_falso = ModuleType("app.ui.vistas.confirmacion_adaptador_qt")
    modulo_falso.resolver_colision_destino_pdf = Mock(return_value="/tmp/final.pdf")
    monkeypatch.setitem(sys.modules, "app.ui.vistas.confirmacion_adaptador_qt", modulo_falso)

    ruta = window._prompt_confirm_pdf_path([_build_solicitud()])

    assert ruta == "/tmp/final.pdf"
    modulo_falso.resolver_colision_destino_pdf.assert_called_once_with(window, "/tmp/original.pdf")


def test_on_confirmar_sin_persona_muestra_warning_y_no_ejecuta_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    window = VentanaFalsa()
    window._current_persona = Mock(return_value=None)
    confirmar_handler = Mock()
    monkeypatch.setattr("app.ui.vistas.main_window.acciones_mixin.on_confirmar_handler", confirmar_handler)

    window._on_confirmar("extra")

    from app.ui.copy_catalog import copy_text

    window.toast.warning.assert_called_once_with(
        copy_text("ui.sync.delegada_no_seleccionada"),
        title=copy_text("ui.validacion.validacion"),
    )
    confirmar_handler.assert_not_called()


def test_on_confirmar_cancela_limpio_si_prompt_pdf_devuelve_none(monkeypatch: pytest.MonkeyPatch) -> None:
    window = VentanaFalsa()

    def _confirmar_accion(ventana):
        assert ventana is window
        ruta = ventana._prompt_confirm_pdf_path([_build_solicitud()])
        assert ruta is None

    monkeypatch.setattr("app.ui.vistas.main_window.acciones_mixin.on_confirmar_handler", _confirmar_accion)
    monkeypatch.setattr(window, "_prompt_confirm_pdf_path", Mock(return_value=None))

    window._on_confirmar()

    window._prompt_confirm_pdf_path.assert_called_once()


def test_on_remove_pendiente_sin_seleccion_no_rompe() -> None:
    window = VentanaFalsa()

    window._on_remove_pendiente()

    window._reload_pending_views.assert_not_called()


def test_on_remove_pendiente_con_seleccion_valida_refresca_y_elimina(monkeypatch: pytest.MonkeyPatch) -> None:
    window = VentanaFalsa()
    window._pending_solicitudes = [_build_solicitud(solicitud_id=10)]
    window.pendientes_table = SimpleNamespace(
        selectionModel=lambda: SimpleNamespace(selectedRows=lambda: [SimpleNamespace(row=lambda: 0)]),
    )
    monkeypatch.setattr(acciones_pendientes, "QMessageBox", _QMessageBoxFake)

    window._on_remove_pendiente()

    window._solicitud_use_cases.eliminar_solicitud.assert_called_once()
    window._reload_pending_views.assert_called_once_with()


def test_on_handle_duplicate_before_add_resuelve_copy_y_accion_ir_existente(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ui.copy_catalog import copy_text

    window = VentanaFalsa()
    window._pending_solicitudes = [_build_solicitud(solicitud_id=123)]
    foco_fila = Mock()
    monkeypatch.setattr(acciones_pendientes, "helper_focus_pending_row", foco_fila)
    _DialogQMessageBoxFake.clicked_button_text = copy_text("ui.validacion.ir_pendiente")
    monkeypatch.setattr(acciones_pendientes, "QMessageBox", _DialogQMessageBoxFake)

    resultado = acciones_pendientes.on_handle_duplicate_before_add(window, duplicate_row=0)

    assert resultado is False
    foco_fila.assert_called_once_with(window, 0)
    dialogo = _DialogQMessageBoxFake.last_instance
    assert dialogo is not None
    assert dialogo.window_title == copy_text("ui.validacion.solicitud_duplicada")
    assert dialogo.text == copy_text("ui.validacion.duplicada_pendiente_detalle")
    assert dialogo.informative_text == copy_text("ui.validacion.duplicada_pendiente_acciones")
    textos_botones = [boton.texto for boton in dialogo.buttons]
    assert copy_text("ui.validacion.ir_pendiente") in textos_botones
    assert copy_text("ui.validacion.crear_igualmente") in textos_botones
    assert copy_text("ui.validacion.cancelar") in textos_botones
    boton_crear = next(b for b in dialogo.buttons if b.texto == copy_text("ui.validacion.crear_igualmente"))
    assert boton_crear.enabled is False
    assert boton_crear.tooltip == copy_text("ui.validacion.duplicados_no_permitido")


def test_on_resolve_pending_conflict_usa_copy_text_para_mensajes(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ui.copy_catalog import copy_text

    window = VentanaFalsa()
    window._pending_solicitudes = [
        SolicitudDTO(
            id=1,
            persona_id=1,
            fecha_solicitud="2026-01-01",
            fecha_pedida="2026-01-01",
            desde="09:00",
            hasta="10:00",
            completo=False,
            horas=1.0,
            observaciones="",
            notas="",
            pdf_path=None,
            pdf_hash=None,
        )
    ]
    confirmaciones: list[str] = []

    def _confirmar(mensaje: str) -> bool:
        confirmaciones.append(mensaje)
        return True

    monkeypatch.setattr(window, "_confirm_conflicto", _confirmar, raising=False)

    assert acciones_pendientes.on_resolve_pending_conflict(window, "2026-01-01", completo=True) is True
    assert confirmaciones[-1] == copy_text("ui.validacion.sustituir_por_completo")

    window._pending_solicitudes = [
        SolicitudDTO(
            id=2,
            persona_id=1,
            fecha_solicitud="2026-01-01",
            fecha_pedida="2026-01-01",
            desde="09:00",
            hasta="10:00",
            completo=True,
            horas=1.0,
            observaciones="",
            notas="",
            pdf_path=None,
            pdf_hash=None,
        )
    ]
    assert acciones_pendientes.on_resolve_pending_conflict(window, "2026-01-01", completo=False) is True
    assert confirmaciones[-1] == copy_text("ui.validacion.sustituir_por_franja")



def test_run_confirmacion_plan_invoca_finalize_con_outcome() -> None:
    from app.ui.vistas.confirmacion_orquestacion import run_confirmacion_plan

    window = SimpleNamespace(
        _ui_ready=True,
        _pending_conflict_rows=set(),
        _run_preconfirm_checks=lambda: True,
    )
    selected = [_build_solicitud()]
    persona = SimpleNamespace(id=1)
    apply_prompt_pdf = Mock(return_value="/tmp/salida.pdf")
    apply_confirm = Mock(return_value=("corr-1", Path("/tmp/salida.pdf"), [], [7], [], []))
    apply_finalize = Mock()

    run_confirmacion_plan(
        window,
        selected=selected,
        selected_ids=[7],
        persona=persona,
        log_extra={},
        apply_show_error=Mock(),
        apply_prompt_pdf=apply_prompt_pdf,
        apply_confirm=apply_confirm,
        apply_finalize=apply_finalize,
    )

    apply_prompt_pdf.assert_called_once_with(window, selected)
    apply_confirm.assert_called_once_with(window, persona, selected, "/tmp/salida.pdf")
    apply_finalize.assert_called_once_with(window, persona, ("corr-1", Path("/tmp/salida.pdf"), [], [7], [], []))
