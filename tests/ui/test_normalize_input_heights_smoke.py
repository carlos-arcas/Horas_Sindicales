from __future__ import annotations

import pytest

from app.application.modo_solo_lectura import crear_estado_modo_solo_lectura
from tests.ui.conftest import require_qt

QApplication = require_qt()
qt_core = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)

from app.ui.vistas.main_window import MainWindow
from app.ui.vistas import main_window_vista


class _NoOpService:
    def __getattr__(self, _name: str):
        return lambda *_args, **_kwargs: []


class _FakeSyncService(_NoOpService):
    def is_configured(self) -> bool:
        return True


def _build_window(monkeypatch: pytest.MonkeyPatch) -> MainWindow:
    monkeypatch.setattr(
        main_window_vista.MainWindow,
        "_load_personas",
        lambda self, select_id=None: None,
    )
    monkeypatch.setattr(
        main_window_vista.MainWindow, "_reload_pending_views", lambda self: None
    )
    monkeypatch.setattr(
        main_window_vista.MainWindow, "_update_global_context", lambda self: None
    )
    monkeypatch.setattr(
        main_window_vista.MainWindow, "_refresh_last_sync_label", lambda self: None
    )
    monkeypatch.setattr(
        main_window_vista.MainWindow, "_update_sync_button_state", lambda self: None
    )
    monkeypatch.setattr(
        main_window_vista.MainWindow, "_update_conflicts_reminder", lambda self: None
    )
    monkeypatch.setattr(
        main_window_vista.MainWindow, "_refresh_health_and_alerts", lambda self: None
    )
    monkeypatch.setattr(
        main_window_vista.MainWindow, "_sync_source_text", lambda self: "stub"
    )
    monkeypatch.setattr(
        main_window_vista.MainWindow, "_sync_scope_text", lambda self: "stub"
    )
    return MainWindow(
        persona_use_cases=_NoOpService(),
        solicitud_use_cases=_NoOpService(),
        grupo_use_cases=_NoOpService(),
        sheets_service=_NoOpService(),
        sync_sheets_use_case=_FakeSyncService(),
        conflicts_service=_NoOpService(),
        health_check_use_case=None,
        alert_engine=None,
        estado_modo_solo_lectura=crear_estado_modo_solo_lectura(lambda: False),
    )


@pytest.mark.ui
@pytest.mark.smoke
@pytest.mark.usefixtures("monkeypatch")
def test_normalize_input_heights_smoke_no_lanza(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window(monkeypatch)

    try:
        window._normalize_input_heights()
        qt_core.QCoreApplication.processEvents()

        expected_height = window.persona_combo.height()
        assert window.fecha_input.height() == expected_height
        assert window.desde_input.height() == expected_height
        assert window.hasta_input.height() == expected_height
    finally:
        window.close()
        app.processEvents()
