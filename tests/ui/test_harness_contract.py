from __future__ import annotations

import pytest

from tests.ui import harness_main_window as harness


@pytest.mark.ui
def test_build_app_reutiliza_instancia_qapplication() -> None:
    app_1 = harness.build_app()
    app_2 = harness.build_app()

    assert app_1 is app_2


@pytest.mark.ui
def test_build_window_tolera_hooks_inexistentes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(harness.main_window_vista.MainWindow, "_reload_pending_views", raising=False)
    app = harness.build_app()
    window = harness.build_window(monkeypatch)

    try:
        harness.pump_events(2)
        assert window is not None
    finally:
        harness.close_window(window)
        app.processEvents()
