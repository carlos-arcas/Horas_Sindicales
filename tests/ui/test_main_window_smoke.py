from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

main_window_vista = pytest.importorskip("app.ui.vistas.main_window_vista", exc_type=ImportError)
MainWindowVista = main_window_vista.MainWindow


@pytest.fixture
def mock_ui_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeApp:
        @staticmethod
        def instance() -> "_FakeApp":
            return _FakeApp()

        def processEvents(self) -> None:
            return None

    class _FakeToastManager:
        def attach_to(self, *_args, **_kwargs) -> None:
            return None

    monkeypatch.setattr(main_window_vista, "QApplication", _FakeApp)
    monkeypatch.setattr(main_window_vista, "QMessageBox", SimpleNamespace(information=lambda *a, **k: None))
    monkeypatch.setattr(main_window_vista, "ToastManager", _FakeToastManager)

    show_calls: list[str] = []

    def _blocked_show(*_args, **_kwargs) -> None:
        show_calls.append("show")

    monkeypatch.setattr(main_window_vista.QMainWindow, "show", _blocked_show)


def _build_window_stub() -> MainWindowVista:
    window = MainWindowVista.__new__(MainWindowVista)
    window._current_persona = Mock(return_value=SimpleNamespace(id=1))
    window.main_tabs = SimpleNamespace(currentIndex=Mock(return_value=1))
    window.historico_delegada_combo = SimpleNamespace(currentData=Mock(return_value=1))
    window.historico_estado_combo = SimpleNamespace(currentData=Mock(return_value="PENDIENTE"))
    window.historico_desde_date = SimpleNamespace(date=Mock(return_value=SimpleNamespace(toString=Mock(return_value="2026-01-01"))))
    window.historico_hasta_date = SimpleNamespace(date=Mock(return_value=SimpleNamespace(toString=Mock(return_value="2026-12-31"))))
    window.historico_search_input = SimpleNamespace(text=Mock(return_value="delegada"))
    table = Mock()
    table.selectionModel.return_value = Mock(selectedRows=Mock(return_value=[]))
    table.model.return_value = Mock()
    table.viewport.return_value = Mock(update=Mock())
    table.isSortingEnabled.return_value = True
    table.updatesEnabled.return_value = True
    window.historico_table = table

    model = Mock()
    model.rowCount.return_value = 1
    window.historico_model = model

    proxy_model = Mock()
    proxy_model.sourceModel.return_value = None
    proxy_model.rowCount.return_value = 1
    window.historico_proxy_model = proxy_model

    window._solicitudes_controller = SimpleNamespace(refresh_historico=Mock(return_value=[SimpleNamespace(id=7)]))
    window._apply_historico_filters = Mock()
    window._update_action_state = Mock()
    window.toast = Mock()
    return window


def test_main_window_vista_refresh_historico_smoke(mock_ui_runtime: None) -> None:
    window = _build_window_stub()

    window._refresh_historico(force=True)

    window._solicitudes_controller.refresh_historico.assert_called_once_with()
    window.historico_model.set_solicitudes.assert_called_once()
    window._apply_historico_filters.assert_called_once_with()
    window._update_action_state.assert_called_once_with()
