from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.application.dto import SolicitudDTO

ConfirmarSinPdfCommand = Literal["RESOLVE_EXISTING", "CREATE_NEW"]


@dataclass(frozen=True)
class ConfirmarSinPdfAction:
    command: ConfirmarSinPdfCommand
    solicitud: SolicitudDTO


def plan_confirmar_sin_pdf(solicitudes: list[SolicitudDTO]) -> tuple[ConfirmarSinPdfAction, ...]:
    return tuple(
        ConfirmarSinPdfAction(
            command="RESOLVE_EXISTING" if solicitud.id is not None else "CREATE_NEW",
            solicitud=solicitud,
        )
        for solicitud in solicitudes
    )

