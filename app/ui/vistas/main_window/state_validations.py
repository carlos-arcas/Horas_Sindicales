from __future__ import annotations

from . import validacion_preventiva


class MainWindowStateValidationMixin:
    """Validaciones reutilizables de la UI para solicitudes/pendientes."""

    def _validate_solicitud_form(self) -> tuple[bool, str]:
        return validacion_preventiva._validate_solicitud_form(self)

    def _focus_first_invalid_field(self) -> None:
        return validacion_preventiva._focus_first_invalid_field(self)

    def _calculate_preview_minutes(self) -> tuple[int | None, bool]:
        return validacion_preventiva._calculate_preview_minutes(self)

    def _manual_hours_minutes(self) -> int:
        return validacion_preventiva._manual_hours_minutes(self)

    def _bind_manual_hours_preview_refresh(self) -> None:
        return validacion_preventiva._bind_manual_hours_preview_refresh(self)

    def _update_solicitudes_status_panel(self) -> None:
        return validacion_preventiva._update_solicitudes_status_panel(self)

    def _format_minutes(self, total_minutes: int) -> str:
        total_minutes = max(0, int(total_minutes))
        horas, minutos = divmod(total_minutes, 60)
        return f"{horas:02d}:{minutos:02d}"
