from __future__ import annotations

import pytest

from tests.ui.conftest import require_qt

QApplication = require_qt()
qt_core = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)

from app.ui.main_window import MainWindow
from app.ui.vistas import main_window_vista


class _NoOpService:
    def __getattr__(self, _name: str):
        return lambda *_args, **_kwargs: []


class _FakeSyncService(_NoOpService):
    def is_configured(self) -> bool:
        return True


@pytest.mark.ui
@pytest.mark.smoke
@pytest.mark.usefixtures("monkeypatch")
def test_ui_arranque_minimo(monkeypatch: pytest.MonkeyPatch) -> None:
    app = QApplication.instance() or QApplication([])

    monkeypatch.setattr(main_window_vista.MainWindow, "_load_personas", lambda self, select_id=None: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_reload_pending_views", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_update_global_context", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_refresh_last_sync_label", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_update_sync_button_state", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_update_conflicts_reminder", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_refresh_health_and_alerts", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_sync_source_text", lambda self: "stub")
    monkeypatch.setattr(main_window_vista.MainWindow, "_sync_scope_text", lambda self: "stub")

    window = MainWindow(
        persona_use_cases=_NoOpService(),
        solicitud_use_cases=_NoOpService(),
        grupo_use_cases=_NoOpService(),
        sheets_service=_NoOpService(),
        sync_sheets_use_case=_FakeSyncService(),
        conflicts_service=_NoOpService(),
        health_check_use_case=None,
        alert_engine=None,
    )

    try:
        window.show()
        qt_core.QCoreApplication.processEvents()
        assert window is not None
        assert hasattr(window, "_on_fecha_changed")
        assert hasattr(window, "_update_solicitud_preview")
        assert window.windowTitle() is not None
        assert getattr(window, "stack", None) is not None
    finally:
        window.close()
        app.processEvents()
