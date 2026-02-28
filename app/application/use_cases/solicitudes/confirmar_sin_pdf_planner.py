from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.application.dto import SolicitudDTO

ConfirmarSinPdfCommand = Literal["RESOLVE_EXISTING", "CREATE_NEW"]
ConfirmarSinPdfReasonCode = Literal[
    "HAS_ID_RESOLVE_EXISTING",
    "MISSING_ID_CREATE_NEW",
]


@dataclass(frozen=True)
class ConfirmarSinPdfPayload:
    solicitud_id: int | None = None
    solicitud: SolicitudDTO | None = None


@dataclass(frozen=True)
class ConfirmarSinPdfAction:
    action_type: ConfirmarSinPdfCommand
    reason_code: ConfirmarSinPdfReasonCode
    payload: ConfirmarSinPdfPayload
    source_solicitud: SolicitudDTO

    @property
    def command(self) -> ConfirmarSinPdfCommand:
        """Alias retrocompatible para consumidores antiguos del planner."""

        return self.action_type

    @property
    def solicitud(self) -> SolicitudDTO:
        """Alias retrocompatible usado por el runner actual."""
        return self.source_solicitud


def plan_confirmar_sin_pdf(solicitudes: list[SolicitudDTO]) -> tuple[ConfirmarSinPdfAction, ...]:
    """Planifica acciones de confirmación sin IO.

    Precedencia de reglas (estable):
    1) Si `solicitud.id` no es `None`, gana siempre `RESOLVE_EXISTING` con
       `reason_code="HAS_ID_RESOLVE_EXISTING"`.
    2) Si `solicitud.id` es `None`, aplica `CREATE_NEW` con
       `reason_code="MISSING_ID_CREATE_NEW"`.
    """

    return tuple(
        ConfirmarSinPdfAction(
            action_type="RESOLVE_EXISTING" if solicitud.id is not None else "CREATE_NEW",
            reason_code=(
                "HAS_ID_RESOLVE_EXISTING"
                if solicitud.id is not None
                else "MISSING_ID_CREATE_NEW"
            ),
            payload=(
                ConfirmarSinPdfPayload(solicitud_id=solicitud.id)
                if solicitud.id is not None
                else ConfirmarSinPdfPayload(solicitud=solicitud)
            ),
            source_solicitud=solicitud,
        )
        for solicitud in solicitudes
    )
