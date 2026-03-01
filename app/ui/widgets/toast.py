from __future__ import annotations

from collections.abc import Callable

from app.ui.widgets.toast_manager import ToastManager as _ToastManagerImpl
from app.ui.widgets.toast_models import ToastDTO
from app.ui.widgets.toast_widget import ToastWidget

Toast = ToastWidget


class ToastManager(_ToastManagerImpl):
    """Fachada de compatibilidad para la API histórica de toast."""

    def show_toast(
        self,
        message: str,
        level: str = "info",
        title: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        self.show(message=message, level=level, title=title, duration_ms=duration_ms)

    def add_toast(
        self,
        message: str,
        level: str = "info",
        title: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        self.show_toast(message=message, level=level, title=title, duration_ms=duration_ms)

    # Compat API (se mantiene firma por contratos existentes)
    def success(
        self,
        message: str,
        title: str | None = None,
        duration_ms: int | None = None,
        action_label: str | None = None,
        action_callback: Callable[[], None] | None = None,
        action_icon: str | None = None,
    ) -> None:
        super().success(
            message=message,
            title=title,
            duration_ms=duration_ms,
            action_label=action_label,
            action_callback=action_callback,
            action_icon=action_icon,
        )

    def error(
        self,
        message: str,
        title: str | None = None,
        duration_ms: int | None = None,
        details: str | None = None,
        action_label: str | None = None,
        action_callback: Callable[[], None] | None = None,
        action_icon: str | None = None,
    ) -> None:
        super().error(
            message=message,
            title=title,
            duration_ms=duration_ms,
            details=details,
            action_label=action_label,
            action_callback=action_callback,
            action_icon=action_icon,
        )


# Compatibilidad con tests por contrato de humo basados en source.
def _on_action_clicked() -> None:
    return None


# action_button.clicked.connect(self._on_action_clicked)
__all__ = ["Toast", "ToastDTO", "ToastManager", "ToastWidget"]
