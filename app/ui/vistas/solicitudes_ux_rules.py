from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolicitudesFocusInput:
    blocking_errors: dict[str, str]
    field_order: tuple[str, ...] = ("delegada", "fecha", "tramo")


@dataclass(frozen=True)
class SolicitudesStatusInput:
    pending_count: int
    has_blocking_errors: bool
    has_runtime_error: bool
    last_action_saved: bool


@dataclass(frozen=True)
class SolicitudesStatusOutput:
    label: str
    hint: str


def resolve_first_invalid_field(data: SolicitudesFocusInput) -> str | None:
    for field in data.field_order:
        if field in data.blocking_errors:
            return field
    if data.blocking_errors:
        return next(iter(data.blocking_errors.keys()))
    return None


def build_solicitudes_status(data: SolicitudesStatusInput) -> SolicitudesStatusOutput:
    if data.has_runtime_error or data.has_blocking_errors:
        return SolicitudesStatusOutput(label="Error", hint="Revisa los campos marcados para continuar.")
    if data.pending_count > 0:
        return SolicitudesStatusOutput(
            label="Pendiente de sync",
            hint="Hay cambios guardados localmente que aún no se han enviado a Google Sheets.",
        )
    if data.last_action_saved:
        return SolicitudesStatusOutput(label="Guardado", hint="Los cambios de la solicitud se guardaron correctamente.")
    return SolicitudesStatusOutput(label="Listo", hint="Puedes completar una nueva solicitud.")
