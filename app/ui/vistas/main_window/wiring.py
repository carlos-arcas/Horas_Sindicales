from __future__ import annotations

from app.ui.vistas.main_window.layout_builder import (
    apply_initial_state_phase,
    build_layout_phase,
    create_widgets,
)


def build_ui(window) -> None:
    create_widgets(window)
    build_layout_phase(window)
    wire_signals_phase(window)
    apply_initial_state_phase(window)
    window._ui_ready = True


def wire_signals_phase(_window) -> None:
    """Fase explícita de señales preservada para compatibilidad."""
