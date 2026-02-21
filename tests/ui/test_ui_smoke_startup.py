from __future__ import annotations

from contextlib import contextmanager
import traceback
from typing import Iterator

import pytest


class _NoOpService:
    def __getattr__(self, _name: str):
        return lambda *_args, **_kwargs: []


class _FakeSyncService(_NoOpService):
    def is_configured(self) -> bool:
        return True


@contextmanager
def _fail_with_full_traceback(context: str) -> Iterator[None]:
    try:
        yield
    except Exception as exc:  # pragma: no cover - exercised only on failure
        raise AssertionError(f"{context}\n{traceback.format_exc()}") from exc


@pytest.mark.ui
def test_ui_smoke_startup_without_real_infra(monkeypatch: pytest.MonkeyPatch) -> None:
    qt_core = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
    qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

    from app.ui.main_window import MainWindow
    from app.ui.vistas import main_window_vista

    q_app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])

    monkeypatch.setattr(main_window_vista.MainWindow, "_load_personas", lambda self, select_id=None: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_reload_pending_views", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_refresh_resumen_kpis", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_update_global_context", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_refresh_last_sync_label", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_update_sync_button_state", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_update_conflicts_reminder", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_refresh_health_and_alerts", lambda self: None)
    monkeypatch.setattr(main_window_vista.MainWindow, "_sync_source_text", lambda self: "stub")
    monkeypatch.setattr(main_window_vista.MainWindow, "_sync_scope_text", lambda self: "stub")

    assert q_app is not None

    with _fail_with_full_traceback("MainWindow explotó durante inicialización/show/processEvents"):
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
            for _ in range(3):
                qt_core.QCoreApplication.processEvents()
        finally:
            window.close()
            qt_core.QCoreApplication.processEvents()
