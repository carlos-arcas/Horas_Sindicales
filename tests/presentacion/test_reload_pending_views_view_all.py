from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.application.dto import SolicitudDTO


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


def _load_data_refresh_module():
    module_path = Path("app/ui/vistas/main_window/data_refresh.py")
    spec = spec_from_file_location("data_refresh_local", module_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _solicitud(solicitud_id: int, persona_id: int) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=persona_id,
        fecha_solicitud="2026-03-01",
        fecha_pedida="2026-03-01",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="",
        notas="",
        pdf_path=None,
        pdf_hash=None,
    )


def test_reload_pending_views_con_ver_todas_no_mantiene_ocultas_por_delegada() -> None:
    data_refresh = _load_data_refresh_module()
    pendientes_todas = [_solicitud(1, 10), _solicitud(2, 20), _solicitud(3, 30)]
    use_cases = SimpleNamespace(
        listar_pendientes_all=lambda: pendientes_todas,
        listar_pendientes_por_persona=lambda _persona_id: [_solicitud(1, 10)],
        listar_pendientes_huerfanas=lambda: [],
    )
    window = SimpleNamespace(
        _pending_view_all=True,
        _solicitud_use_cases=use_cases,
        _current_persona=lambda: SimpleNamespace(id=10),
        pending_filter_warning=SimpleNamespace(setVisible=Mock(), setText=Mock()),
        revisar_ocultas_button=SimpleNamespace(setVisible=Mock(), setText=Mock()),
        huerfanas_model=SimpleNamespace(set_solicitudes=Mock()),
        huerfanas_label=SimpleNamespace(setVisible=Mock()),
        huerfanas_table=SimpleNamespace(setVisible=Mock()),
        eliminar_huerfana_button=SimpleNamespace(setVisible=Mock()),
        _refresh_pending_ui_state=Mock(),
        _pending_selection_anchor_row=5,
        _hidden_pendientes=[],
        _orphan_pendientes=[],
        _pending_solicitudes=[],
        _pending_all_solicitudes=[],
        _pending_otras_delegadas=[],
    )

    data_refresh.reload_pending_views(window)

    assert [sol.id for sol in window._pending_solicitudes] == [1, 2, 3]
    assert window._hidden_pendientes == []
    assert window._pending_otras_delegadas == []
    assert window._pending_selection_anchor_row is None
    window._refresh_pending_ui_state.assert_called_once_with()
