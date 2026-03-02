from __future__ import annotations

import pytest

try:
    from app.ui.vistas.main_window.state_controller import MainWindow
except ImportError as exc:  # pragma: no cover - depende del entorno de Qt
    pytest.skip(f"Qt no disponible para este test: {exc}", allow_module_level=True)


class Dummy:
    pass


def test_update_conflicts_reminder_existe_en_main_window() -> None:
    assert hasattr(MainWindow, "_update_conflicts_reminder")


def test_update_conflicts_reminder_early_no_explota_sin_widgets() -> None:
    dummy = Dummy()

    MainWindow._update_conflicts_reminder(dummy)
