from __future__ import annotations

import pytest
from tests.ui.conftest import require_qt

QApplication = require_qt()


class _NoOpService:
    def __getattr__(self, _name: str):
        return lambda *_args, **_kwargs: []


class _FakeSyncService(_NoOpService):
    def is_configured(self) -> bool:
        return True


@pytest.mark.ui
def test_event_filter_accepts_qkeyevent_without_nameerror(monkeypatch: pytest.MonkeyPatch) -> None:
    qt_core = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
    qt_gui = pytest.importorskip("PySide6.QtGui", exc_type=ImportError)
    qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

    from app.ui.main_window import MainWindow
    from app.ui.vistas import main_window_vista

    app = QApplication.instance() or QApplication([])
    assert app is not None

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
        key_event = qt_gui.QKeyEvent(qt_core.QEvent.KeyPress, qt_core.Qt.Key_Return, qt_core.Qt.NoModifier)
        handled = window.eventFilter(window.notas_input, key_event)
        assert isinstance(handled, bool)
    finally:
        window.close()
        qt_core.QCoreApplication.processEvents()
