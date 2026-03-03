from __future__ import annotations

import pytest

from tests.ui.harness_main_window import QTabWidget, build_app, build_window, close_window, pump_events


@pytest.mark.ui
@pytest.mark.smoke
def test_ui_arranque_minimo(monkeypatch: pytest.MonkeyPatch) -> None:
    app = build_app()
    window = build_window(monkeypatch)

    try:
        window.show()
        pump_events(3)

        assert window.isVisible()
        assert bool(window.windowTitle())
        assert hasattr(window, "main_tabs")
        assert QTabWidget is not None
        assert isinstance(window.main_tabs, QTabWidget)
        assert window.main_tabs.count() >= 1
        assert callable(getattr(window, "_switch_sidebar_page", None))
    finally:
        close_window(window)
        app.processEvents()
