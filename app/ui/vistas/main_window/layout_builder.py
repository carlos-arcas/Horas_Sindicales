from __future__ import annotations

from app.ui.vistas.builders.main_window_builders import (
    build_main_window_widgets,
    build_shell_layout,
    build_status_bar,
)


def create_widgets(window) -> None:
    build_main_window_widgets(window)


def build_shell(window) -> None:
    build_shell_layout(window)


def build_status(window) -> None:
    build_status_bar(window)


def build_layout_phase(_window) -> None:
    """Fase explícita de layout preservada para compatibilidad."""


def apply_initial_state_phase(_window) -> None:
    """Fase explícita de estado inicial preservada para compatibilidad."""
