from __future__ import annotations

from app.ui.vistas.main_window import layout_builder


def build_ui(window) -> None:
    layout_builder.create_widgets(window)
    layout_builder.build_layout_phase(window)
    wire_signals_phase(window)
    layout_builder.apply_initial_state_phase(window)
    window._ui_ready = True


def wire_signals_phase(_window) -> None:
    """Fase explícita de señales preservada para compatibilidad."""
