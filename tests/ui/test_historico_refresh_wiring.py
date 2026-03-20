from __future__ import annotations

import ast
import importlib
from pathlib import Path
import sys
import types
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.application.dto import PersonaDTO, SolicitudDTO
from app.ui.vistas.historico_refresh_logic import build_historico_rows

pytestmark = pytest.mark.headless_safe

VISTA_PATH = Path("app/ui/vistas/main_window_vista.py")


@pytest.fixture
def main_window_vista_mod(monkeypatch: pytest.MonkeyPatch):
    class _QMainWindow:
        pass

    class _QTimer:
        @staticmethod
        def singleShot(_delay: int, _callback: object) -> None:
            return None

    qt_compat = types.ModuleType("app.ui.qt_compat")
    qt_compat.QMainWindow = _QMainWindow
    qt_compat.QTimer = _QTimer

    layout_builder = types.ModuleType("app.ui.vistas.main_window.layout_builder")
    layout_builder.HistoricoDetalleDialog = type("HistoricoDetalleDialog", (), {})
    layout_builder.OptionalConfirmDialog = type("OptionalConfirmDialog", (), {})
    layout_builder.PdfPreviewDialog = type("PdfPreviewDialog", (), {})

    navegacion = types.ModuleType("app.ui.vistas.main_window.navegacion_mixin")
    navegacion.TAB_HISTORICO = 1

    state_controller = types.ModuleType("app.ui.vistas.main_window.state_controller")
    state_controller.MainWindow = type("_MainWindowBase", (), {})

    state_helpers = types.ModuleType("app.ui.vistas.main_window.state_helpers")
    state_helpers.resolve_active_delegada_id = lambda *args, **kwargs: None

    init_refresh = types.ModuleType("app.ui.vistas.init_refresh")
    init_refresh.run_init_refresh = lambda **kwargs: None

    modulos = {
        "app.ui.qt_compat": qt_compat,
        "app.ui.vistas.main_window.layout_builder": layout_builder,
        "app.ui.vistas.main_window.navegacion_mixin": navegacion,
        "app.ui.vistas.main_window.state_controller": state_controller,
        "app.ui.vistas.main_window.state_helpers": state_helpers,
        "app.ui.vistas.init_refresh": init_refresh,
    }
    for nombre, modulo in modulos.items():
        monkeypatch.setitem(sys.modules, nombre, modulo)

    sys.modules.pop("app.ui.vistas.main_window_vista", None)
    modulo = importlib.import_module("app.ui.vistas.main_window_vista")
    yield modulo
    sys.modules.pop("app.ui.vistas.main_window_vista", None)


def _persona(persona_id: int | None, nombre: str) -> PersonaDTO:
    return PersonaDTO(
        id=persona_id,
        nombre=nombre,
        genero="F",
        horas_mes=600,
        horas_ano=7200,
        is_active=True,
        cuad_lun_man_min=0,
        cuad_lun_tar_min=0,
        cuad_mar_man_min=0,
        cuad_mar_tar_min=0,
        cuad_mie_man_min=0,
        cuad_mie_tar_min=0,
        cuad_jue_man_min=0,
        cuad_jue_tar_min=0,
        cuad_vie_man_min=0,
        cuad_vie_tar_min=0,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )


def _solicitud(
    solicitud_id: int, persona_id: int, fecha: str, desde: str, hasta: str
) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=persona_id,
        fecha_solicitud=fecha,
        fecha_pedida=fecha,
        desde=desde,
        hasta=hasta,
        completo=False,
        horas=1.0,
        observaciones="",
        pdf_path=None,
        pdf_hash=None,
        notas="",
    )


def _class_and_methods() -> tuple[ast.ClassDef, dict[str, ast.FunctionDef]]:
    module = ast.parse(VISTA_PATH.read_text(encoding="utf-8"))
    main_window = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
    )
    methods = {
        node.name: node
        for node in main_window.body
        if isinstance(node, ast.FunctionDef)
    }
    return main_window, methods


def _contains_call(method: ast.FunctionDef, attr_name: str) -> bool:
    for node in ast.walk(method):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == attr_name
        ):
            return True
    return False


def _contains_refresh_call(method: ast.FunctionDef, force_value: bool) -> bool:
    for node in ast.walk(method):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "_refresh_historico":
            continue
        for keyword in node.keywords:
            if keyword.arg == "force" and isinstance(keyword.value, ast.Constant):
                return keyword.value.value is force_value
    return False


def test_post_init_load_wires_historico_refresh() -> None:
    _, methods = _class_and_methods()
    assert "_post_init_load" in methods
    assert _contains_refresh_call(methods["_post_init_load"], force_value=True)


def test_tab_changed_wires_historico_refresh() -> None:
    _, methods = _class_and_methods()
    assert "_on_main_tab_changed" in methods
    assert _contains_refresh_call(methods["_on_main_tab_changed"], force_value=False)


def test_refresh_historico_fachada_delega_en_super_sin_consulta_directa() -> None:
    _, methods = _class_and_methods()
    assert "_refresh_historico" in methods
    assert not _contains_call(methods["_refresh_historico"], "refresh_historico")
    assert _contains_call(methods["_refresh_historico"], "_refresh_historico")


def test_build_historico_rows_collects_all_persona_rows() -> None:
    personas = [
        _persona(1, "Ana"),
        _persona(None, "Sin id"),
        _persona(2, "Bea"),
    ]
    solicitud_a = _solicitud(11, 1, "2026-01-10", "09:00", "10:00")
    solicitud_b = _solicitud(22, 2, "2026-01-11", "10:00", "11:00")

    def fake_listar(persona_id: int) -> list[SolicitudDTO]:
        if persona_id == 1:
            return [solicitud_a]
        if persona_id == 2:
            return [solicitud_b]
        return []

    rows = build_historico_rows(personas, fake_listar)

    assert rows == [solicitud_a, solicitud_b]


def test_post_init_load_programa_warmup_sync(
    monkeypatch: pytest.MonkeyPatch,
    main_window_vista_mod,
) -> None:
    modulo = main_window_vista_mod
    cola_refresh: list[object] = []
    cola_timer: list[tuple[int, object]] = []

    def _fake_run_init_refresh(**kwargs):
        cola_refresh.append(kwargs)

    monkeypatch.setattr(modulo, "run_init_refresh", _fake_run_init_refresh)
    monkeypatch.setattr(
        modulo.QTimer,
        "singleShot",
        lambda delay, callback: cola_timer.append((delay, callback)),
    )

    class _VentanaFalsa:
        def __init__(self) -> None:
            self.calls: list[str] = []
            self._warmup_sync_client = lambda: self.calls.append("warmup")

        def _refresh_saldos(self) -> None:
            self.calls.append("resumen")

        def _reload_pending_views(self) -> None:
            self.calls.append("pendientes")

        def _refresh_historico(self, *, force: bool = False) -> None:
            self.calls.append(f"historico:{force}")

    window = _VentanaFalsa()

    modulo.MainWindow._post_init_load(window)

    assert len(cola_refresh) == 1
    refresh_kwargs = cola_refresh[0]
    assert callable(refresh_kwargs["scheduler"])
    assert cola_timer == [(0, window._warmup_sync_client)]

    refresh_kwargs["refresh_historico"]()

    assert window.calls == ["historico:True"]


def test_post_init_load_scheduler_sigue_siendo_diferido(
    monkeypatch: pytest.MonkeyPatch,
    main_window_vista_mod,
) -> None:
    modulo = main_window_vista_mod
    scheduler_callbacks: list[object] = []

    monkeypatch.setattr(
        modulo.QTimer,
        "singleShot",
        lambda delay, callback: scheduler_callbacks.append((delay, callback)),
    )

    def _fake_run_init_refresh(**kwargs):
        kwargs["scheduler"](lambda: None)

    monkeypatch.setattr(modulo, "run_init_refresh", _fake_run_init_refresh)

    class _VentanaFalsa:
        def _warmup_sync_client(self) -> None:
            return None

        def _refresh_saldos(self) -> None:
            raise AssertionError("no debe ejecutarse inline")

        def _reload_pending_views(self) -> None:
            raise AssertionError("no debe ejecutarse inline")

        def _refresh_historico(self, *, force: bool = False) -> None:
            raise AssertionError("no debe ejecutarse inline")

    modulo.MainWindow._post_init_load(_VentanaFalsa())

    assert len(scheduler_callbacks) == 2
    assert all(delay == 0 for delay, _ in scheduler_callbacks)


def test_data_refresh_historico_ejecuta_una_sola_consulta_y_aplica_estado(monkeypatch: pytest.MonkeyPatch) -> None:
    helpers_mod = types.ModuleType("app.ui.vistas.main_window_helpers")
    helpers_mod.build_historico_filters_payload = Mock(return_value={"force": True})
    helpers_mod.handle_historico_render_mismatch = Mock(return_value=1)
    monkeypatch.setitem(sys.modules, "app.ui.vistas.main_window_helpers", helpers_mod)

    data_refresh = importlib.import_module("app.ui.vistas.main_window.data_refresh")
    data_refresh = importlib.reload(data_refresh)

    solicitudes = [SimpleNamespace(id=7)]
    table = SimpleNamespace(
        isSortingEnabled=Mock(return_value=True),
        setUpdatesEnabled=Mock(),
        setSortingEnabled=Mock(),
        sortByColumn=Mock(),
    )
    model = SimpleNamespace(set_solicitudes=Mock())
    proxy_model = SimpleNamespace(
        sourceModel=Mock(return_value=None),
        setSourceModel=Mock(),
        invalidateFilter=Mock(),
        invalidate=Mock(),
        rowCount=Mock(return_value=1),
    )
    controller = SimpleNamespace(refresh_historico=Mock(return_value=solicitudes))
    window = SimpleNamespace(
        historico_table=table,
        historico_model=model,
        historico_proxy_model=proxy_model,
        _current_persona=Mock(return_value=SimpleNamespace(id=3)),
        historico_delegada_combo=SimpleNamespace(currentData=Mock(return_value=3)),
        historico_estado_combo=SimpleNamespace(currentData=Mock(return_value="PENDIENTE")),
        historico_desde_date=SimpleNamespace(date=Mock(return_value=SimpleNamespace(toString=Mock(return_value="2026-01-01")))),
        historico_hasta_date=SimpleNamespace(date=Mock(return_value=SimpleNamespace(toString=Mock(return_value="2026-12-31")))),
        historico_search_input=SimpleNamespace(text=Mock(return_value="delegada")),
        main_tabs=SimpleNamespace(currentIndex=Mock(return_value=1)),
        _solicitudes_controller=controller,
        _apply_historico_filters=Mock(),
        _update_action_state=Mock(),
        _historico_ids_seleccionados={99},
        eliminar_button=SimpleNamespace(setText=Mock()),
        toast=Mock(),
    )

    scheduled: list[tuple[int, object]] = []
    monkeypatch.setattr(
        data_refresh.QTimer,
        "singleShot",
        lambda delay, callback: scheduled.append((delay, callback)),
    )

    data_refresh.refresh_historico(window, force=True)

    controller.refresh_historico.assert_called_once_with()
    model.set_solicitudes.assert_called_once_with(solicitudes)
    window._apply_historico_filters.assert_called_once_with()
    window._update_action_state.assert_called_once_with()
    assert window._historico_ids_seleccionados == set()
    proxy_model.setSourceModel.assert_called_once_with(model)
    assert scheduled and scheduled[0][0] == 0


def test_main_window_refresh_historico_propaga_force_al_flujo_base(
    monkeypatch: pytest.MonkeyPatch,
    main_window_vista_mod,
) -> None:
    modulo = main_window_vista_mod
    base_calls: list[bool] = []
    base_class = modulo.MainWindow.__mro__[1]

    def _fake_base_refresh(self, *, force: bool = False) -> None:
        base_calls.append(force)

    monkeypatch.setattr(base_class, "_refresh_historico", _fake_base_refresh, raising=False)
    window = modulo.MainWindow.__new__(modulo.MainWindow)
    window._solicitudes_controller = SimpleNamespace(refresh_historico=Mock())

    modulo.MainWindow._refresh_historico(window, force=False)
    modulo.MainWindow._refresh_historico(window, force=True)

    window._solicitudes_controller.refresh_historico.assert_not_called()
    assert base_calls == [False, True]
