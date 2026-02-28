from __future__ import annotations

from pathlib import Path

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
def test_main_window_contract_public_attributes(monkeypatch: pytest.MonkeyPatch) -> None:
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
    expected_attrs = [
        "main_tabs",
        "persona_combo",
        "pendientes_table",
        "historico_table",
        "agregar_button",
        "confirmar_button",
        "sync_button",
        "status_label",
    ]
    for attr in expected_attrs:
        assert hasattr(window, attr), f"MainWindow no expone atributo público esperado: {attr}"
    window.close()


def test_main_window_vista_imports_without_cycles() -> None:
    __import__("app.ui.vistas.main_window_vista")
    __import__("app.ui.vistas.main_window.layout_builder")
    __import__("app.ui.vistas.main_window.state_controller")
    __import__("app.ui.vistas.main_window.data_refresh")
    __import__("app.ui.vistas.main_window.form_handlers")
    __import__("app.ui.vistas.main_window.wiring")


def test_main_window_vista_loc_guardrail() -> None:
    loc = len(Path("app/ui/vistas/main_window_vista.py").read_text(encoding="utf-8").splitlines())
    assert loc <= 2800, f"Guardrail temporal excedido: {loc} LOC"
