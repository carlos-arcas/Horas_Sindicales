from __future__ import annotations

import sys
from types import SimpleNamespace
import types

import pytest

from app.ui.vistas.main_window import state_bindings, state_historico


pytestmark = pytest.mark.headless_safe


class _Index:
    def __init__(self, row: int) -> None:
        self._row = row

    def row(self) -> int:
        return self._row


class _SelectionModelStub:
    def __init__(self, rows: list[int]) -> None:
        self._rows = rows

    def selectedRows(self):  # noqa: N802
        return [_Index(row) for row in self._rows]


class _TableStub:
    def __init__(self, selection_model: _SelectionModelStub | None) -> None:
        self._selection_model = selection_model

    def selectionModel(self):  # noqa: N802
        return self._selection_model


class _ProxyModelStub:
    def mapToSource(self, index: _Index) -> _Index:  # noqa: N802
        return index


class _HistoricoModelStub:
    def __init__(self, solicitudes: dict[int, object]) -> None:
        self._solicitudes = solicitudes

    def solicitud_at(self, row: int) -> object | None:
        return self._solicitudes.get(row)


def _build_window(rows: list[int] | None) -> SimpleNamespace:
    selection_model = None if rows is None else _SelectionModelStub(rows)
    solicitudes = {
        0: SimpleNamespace(id=101, descripcion="primera"),
        1: SimpleNamespace(id=202, descripcion="segunda"),
    }
    return SimpleNamespace(
        historico_table=_TableStub(selection_model),
        historico_proxy_model=_ProxyModelStub(),
        historico_model=_HistoricoModelStub(solicitudes),
    )


def test_selected_historico_helpers_no_rompen_sin_selection_model() -> None:
    window = _build_window(rows=None)
    window._selected_historico_solicitudes = lambda: state_historico.obtener_solicitudes_historico_seleccionadas(window)

    assert state_historico.obtener_solicitudes_historico_seleccionadas(window) == []
    assert state_historico.obtener_solicitud_historico_seleccionada(window) is None


def test_selected_historico_helpers_devuelven_solicitudes_con_selection_model() -> None:
    window = _build_window(rows=[1, 0])
    window._selected_historico_solicitudes = lambda: state_historico.obtener_solicitudes_historico_seleccionadas(window)

    seleccionadas = state_historico.obtener_solicitudes_historico_seleccionadas(window)

    assert [solicitud.id for solicitud in seleccionadas] == [202, 101]
    assert state_historico.obtener_solicitud_historico_seleccionada(window).id == 202


def test_registrar_state_bindings_usa_fuente_canonica_robusta_para_historico(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _MainWindowFalsa:
        pass

    historico_actions_stub = types.ModuleType("app.ui.vistas.historico_actions")
    for nombre in (
        "apply_historico_filters",
        "apply_historico_default_range",
        "apply_historico_last_30_days",
        "on_historico_periodo_mode_changed",
        "on_historico_apply_filters",
        "on_historico_filter_changed",
        "on_historico_search_text_changed",
        "build_historico_filters",
        "configure_historico_focus_order",
        "focus_historico_search",
        "sync_historico_select_all_visible_state",
        "on_export_historico_pdf",
    ):
        setattr(historico_actions_stub, nombre, lambda *_args, **_kwargs: None)
    monkeypatch.setitem(sys.modules, "app.ui.vistas.historico_actions", historico_actions_stub)

    state_bindings.registrar_state_bindings(_MainWindowFalsa)

    window_data = _build_window(rows=None)
    window = _MainWindowFalsa()
    window.historico_table = window_data.historico_table
    window.historico_proxy_model = window_data.historico_proxy_model
    window.historico_model = window_data.historico_model

    assert _MainWindowFalsa._selected_historico_solicitudes(window) == []
    assert _MainWindowFalsa._selected_historico(window) is None

    assert _MainWindowFalsa._selected_historico_solicitudes.__closure__ is not None
    fn_canonica = _MainWindowFalsa._selected_historico_solicitudes.__closure__[0].cell_contents
    fn_canonica_detalle = _MainWindowFalsa._selected_historico.__closure__[0].cell_contents
    assert fn_canonica is state_historico.obtener_solicitudes_historico_seleccionadas
    assert fn_canonica_detalle is state_historico.obtener_solicitud_historico_seleccionada
