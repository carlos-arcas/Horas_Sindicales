from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.application.dto import SolicitudDTO
from app.domain.models import Persona

PdfActionType = Literal["GENERATE_PDF", "HASH_FILE", "UPDATE_STATUS"]
PdfReasonCode = Literal[
    "NO_SOLICITUDES",
    "PERSONA_NO_ENCONTRADA",
    "GENERADOR_NO_CONFIGURADO",
    "PLAN_READY",
]


@dataclass(frozen=True)
class PdfConfirmadasEntrada:
    """Snapshot inmutable de entrada para planificar la generación PDF sin IO."""

    creadas: tuple[SolicitudDTO, ...]
    destino: Path
    persona: Persona | None
    generador_configurado: bool
    intro_text: str | None
    logo_path: str | None
    include_hours_in_horario: bool | None


@dataclass(frozen=True)
class PdfAction:
    action_type: PdfActionType
    reason_code: str
    solicitudes: tuple[SolicitudDTO, ...] = ()
    solicitud: SolicitudDTO | None = None
    persona: Persona | None = None
    destino: Path | None = None
    intro_text: str | None = None
    logo_path: str | None = None
    include_hours_in_horario: bool | None = None


@dataclass(frozen=True)
class PdfConfirmadasPlan:
    actions: tuple[PdfAction, ...]
    reason_code: PdfReasonCode


def plan_pdf_confirmadas(entrada: PdfConfirmadasEntrada) -> PdfConfirmadasPlan:
    """Construye el plan sin efectos secundarios con precedencia estable de reason_code.

    Precedencia (de mayor a menor):
    1) NO_SOLICITUDES
    2) PERSONA_NO_ENCONTRADA
    3) GENERADOR_NO_CONFIGURADO
    4) PLAN_READY
    """

    if not entrada.creadas:
        return PdfConfirmadasPlan(actions=(), reason_code="NO_SOLICITUDES")

    if entrada.persona is None:
        return PdfConfirmadasPlan(actions=(), reason_code="PERSONA_NO_ENCONTRADA")

    if not entrada.generador_configurado:
        return PdfConfirmadasPlan(actions=(), reason_code="GENERADOR_NO_CONFIGURADO")

    actions: list[PdfAction] = [
        PdfAction(
            action_type="GENERATE_PDF",
            reason_code="PLAN_READY",
            solicitudes=entrada.creadas,
            persona=entrada.persona,
            destino=entrada.destino,
            intro_text=entrada.intro_text,
            logo_path=entrada.logo_path,
            include_hours_in_horario=entrada.include_hours_in_horario,
        ),
        PdfAction(action_type="HASH_FILE", reason_code="PLAN_READY"),
    ]
    actions.extend(
        PdfAction(action_type="UPDATE_STATUS", reason_code="PLAN_READY", solicitud=solicitud)
        for solicitud in entrada.creadas
    )
    return PdfConfirmadasPlan(actions=tuple(actions), reason_code="PLAN_READY")
