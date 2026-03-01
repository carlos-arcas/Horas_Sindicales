from __future__ import annotations

import pytest


@pytest.mark.headless_safe
@pytest.mark.smoke
def test_ui_headless_fallback_smoke() -> None:
    """Smoke mínimo para CI cuando Qt no está disponible en el runner."""
    from app.ui import main_window as main_window_module

    assert hasattr(main_window_module, "MainWindow")
