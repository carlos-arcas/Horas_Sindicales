from __future__ import annotations

import pytest

from tests.ui.harness_main_window import build_app, build_window, close_window, pump_events


@pytest.mark.ui
@pytest.mark.smoke
def test_ui_navegacion_minima_cambia_tab(monkeypatch: pytest.MonkeyPatch) -> None:
    app = build_app()
    window = build_window(monkeypatch)

    try:
        window.show()
        pump_events(3)
        total_tabs = window.main_tabs.count()
        if total_tabs < 2:
            pytest.skip("Navegación mínima omitida: main_tabs tiene menos de 2 pestañas en este entorno.")

        target_index = min(1, total_tabs - 1)
        switch_page = getattr(window, "_switch_sidebar_page", None)
        if callable(switch_page):
            switch_page(target_index)
        else:
            window.main_tabs.setCurrentIndex(target_index)

        pump_events(3)
        assert window.main_tabs.currentIndex() == target_index
    finally:
        close_window(window)
        app.processEvents()
