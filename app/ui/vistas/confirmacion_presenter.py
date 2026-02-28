from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReasonCode = Literal[
    "ui_not_ready",
    "no_pending_rows",
    "preconfirm_checks",
    "no_persona",
    "conflictos_pendientes",
    "pdf_path_cancelado",
    "execute_confirm_none",
    "ready_for_prompt",
    "ready_for_confirm",
    "confirmed",
]


@dataclass(frozen=True)
class ConfirmacionEntrada:
    """Estado mínimo de UI para planificar la confirmación sin depender de Qt/IO.

    Reglas implícitas extraídas del flujo legacy:
    1) El orden de precedencia de bloqueos es estricto.
    2) Si aún no se pidió ruta de PDF, el siguiente paso es abrir diálogo.
    3) Si ya se pidió PDF y se canceló, se termina sin confirmar.
    4) Tras ejecutar confirmación, solo se finaliza cuando hay outcome válido.
    """

    ui_ready: bool
    selected_ids: tuple[int | None, ...]
    preconfirm_checks_ok: bool
    persona_selected: bool
    has_pending_conflicts: bool
    pdf_prompted: bool = False
    pdf_path: str | None = None
    execute_attempted: bool = False
    execute_succeeded: bool | None = None
    no_pending_message: str = "No hay pendientes"
    no_pending_title: str = "Sin pendientes"
    conflict_message: str = "Hay peticiones con horarios solapados. Elimina/modifica el conflicto para confirmar."
    conflict_title: str = "Conflictos detectados"


@dataclass(frozen=True)
class ConfirmAction:
    action_type: str
    reason_code: str | None = None
    message: str | None = None
    title: str | None = None


@dataclass(frozen=True)
class ConfirmacionDecision:
    allow_confirm: bool
    reason_code: ReasonCode
    severity: Literal["info", "warning", "error", "success"]
    mensaje_usuario: str | None
    acciones_ui: tuple[str, ...]


@dataclass(frozen=True)
class ConfirmacionPlan:
    decision: ConfirmacionDecision
    actions: tuple[ConfirmAction, ...]


def aplicar_reglas_confirmacion(entrada: ConfirmacionEntrada) -> ConfirmacionDecision:
    if not entrada.ui_ready:
        return ConfirmacionDecision(False, "ui_not_ready", "info", None, ("LOG_EARLY_RETURN",))
    if not entrada.selected_ids:
        return ConfirmacionDecision(
            False,
            "no_pending_rows",
            "warning",
            entrada.no_pending_message,
            ("SHOW_ERROR", "LOG_EARLY_RETURN"),
        )
    if not entrada.preconfirm_checks_ok:
        return ConfirmacionDecision(False, "preconfirm_checks", "warning", None, ("LOG_EARLY_RETURN",))
    if not entrada.persona_selected:
        return ConfirmacionDecision(False, "no_persona", "warning", None, ("LOG_EARLY_RETURN",))
    if entrada.has_pending_conflicts:
        return ConfirmacionDecision(
            False,
            "conflictos_pendientes",
            "warning",
            entrada.conflict_message,
            ("SHOW_ERROR", "LOG_EARLY_RETURN"),
        )
    if not entrada.pdf_prompted:
        return ConfirmacionDecision(True, "ready_for_prompt", "info", None, ("PROMPT_PDF",))
    if entrada.pdf_path is None:
        return ConfirmacionDecision(False, "pdf_path_cancelado", "info", None, ("LOG_EARLY_RETURN",))
    if not entrada.execute_attempted:
        return ConfirmacionDecision(True, "ready_for_confirm", "info", None, ("PREPARE_PAYLOAD", "CONFIRM"))
    if not entrada.execute_succeeded:
        return ConfirmacionDecision(False, "execute_confirm_none", "error", None, ("LOG_EARLY_RETURN",))
    return ConfirmacionDecision(
        True,
        "confirmed",
        "success",
        None,
        ("FINALIZE_CONFIRMATION", "RESET_FORM", "REFRESH_TABLE", "SHOW_TOAST"),
    )


def _actions_from_decision(decision: ConfirmacionDecision, entrada: ConfirmacionEntrada) -> tuple[ConfirmAction, ...]:
    actions: list[ConfirmAction] = []
    for action_name in decision.acciones_ui:
        if action_name == "SHOW_ERROR":
            if decision.reason_code == "no_pending_rows":
                actions.append(
                    ConfirmAction("SHOW_ERROR", reason_code=decision.reason_code, message=entrada.no_pending_message, title=entrada.no_pending_title)
                )
            elif decision.reason_code == "conflictos_pendientes":
                actions.append(
                    ConfirmAction("SHOW_ERROR", reason_code=decision.reason_code, message=entrada.conflict_message, title=entrada.conflict_title)
                )
            else:
                actions.append(ConfirmAction("SHOW_ERROR", reason_code=decision.reason_code, message=decision.mensaje_usuario))
        else:
            actions.append(ConfirmAction(action_name, reason_code=decision.reason_code, message=decision.mensaje_usuario))
    return tuple(actions)


def build_confirmacion_plan(entrada: ConfirmacionEntrada) -> ConfirmacionPlan:
    decision = aplicar_reglas_confirmacion(entrada)
    return ConfirmacionPlan(decision=decision, actions=_actions_from_decision(decision, entrada))


def plan_confirmacion(entrada: ConfirmacionEntrada) -> list[ConfirmAction]:
    return list(build_confirmacion_plan(entrada).actions)
