from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

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
    """Estado mínimo de UI para planificar la confirmación sin depender de Qt/IO."""

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


RuleBuilder = Callable[[ConfirmacionEntrada], ConfirmacionDecision]


def _decision_ui_not_ready(_: ConfirmacionEntrada) -> ConfirmacionDecision:
    return ConfirmacionDecision(False, "ui_not_ready", "info", None, ("LOG_EARLY_RETURN",))


def _decision_no_pending(entrada: ConfirmacionEntrada) -> ConfirmacionDecision:
    return ConfirmacionDecision(
        False,
        "no_pending_rows",
        "warning",
        entrada.no_pending_message,
        ("SHOW_ERROR", "LOG_EARLY_RETURN"),
    )


def _decision_preconfirm(_: ConfirmacionEntrada) -> ConfirmacionDecision:
    return ConfirmacionDecision(False, "preconfirm_checks", "warning", None, ("LOG_EARLY_RETURN",))


def _decision_no_persona(_: ConfirmacionEntrada) -> ConfirmacionDecision:
    return ConfirmacionDecision(False, "no_persona", "warning", None, ("LOG_EARLY_RETURN",))


def _decision_conflictos(entrada: ConfirmacionEntrada) -> ConfirmacionDecision:
    return ConfirmacionDecision(
        False,
        "conflictos_pendientes",
        "warning",
        entrada.conflict_message,
        ("SHOW_ERROR", "LOG_EARLY_RETURN"),
    )


def _decision_prompt(_: ConfirmacionEntrada) -> ConfirmacionDecision:
    return ConfirmacionDecision(True, "ready_for_prompt", "info", None, ("PROMPT_PDF",))


def _decision_pdf_cancelado(_: ConfirmacionEntrada) -> ConfirmacionDecision:
    return ConfirmacionDecision(False, "pdf_path_cancelado", "info", None, ("LOG_EARLY_RETURN",))


def _decision_ready_confirm(_: ConfirmacionEntrada) -> ConfirmacionDecision:
    return ConfirmacionDecision(True, "ready_for_confirm", "info", None, ("PREPARE_PAYLOAD", "CONFIRM"))


def _decision_execute_none(_: ConfirmacionEntrada) -> ConfirmacionDecision:
    return ConfirmacionDecision(False, "execute_confirm_none", "error", None, ("LOG_EARLY_RETURN",))


def _decision_confirmed(_: ConfirmacionEntrada) -> ConfirmacionDecision:
    return ConfirmacionDecision(
        True,
        "confirmed",
        "success",
        None,
        ("FINALIZE_CONFIRMATION", "RESET_FORM", "REFRESH_TABLE", "SHOW_TOAST"),
    )


RULES: tuple[tuple[Callable[[ConfirmacionEntrada], bool], RuleBuilder], ...] = (
    (lambda e: not e.ui_ready, _decision_ui_not_ready),
    (lambda e: not e.selected_ids, _decision_no_pending),
    (lambda e: not e.preconfirm_checks_ok, _decision_preconfirm),
    (lambda e: not e.persona_selected, _decision_no_persona),
    (lambda e: e.has_pending_conflicts, _decision_conflictos),
    (lambda e: not e.pdf_prompted, _decision_prompt),
    (lambda e: e.pdf_path is None, _decision_pdf_cancelado),
    (lambda e: not e.execute_attempted, _decision_ready_confirm),
    (lambda e: not e.execute_succeeded, _decision_execute_none),
    (lambda _e: True, _decision_confirmed),
)


def aplicar_reglas_confirmacion(entrada: ConfirmacionEntrada) -> ConfirmacionDecision:
    for predicate, decision_builder in RULES:
        if predicate(entrada):
            return decision_builder(entrada)
    return _decision_confirmed(entrada)


def _actions_from_decision(decision: ConfirmacionDecision, entrada: ConfirmacionEntrada) -> tuple[ConfirmAction, ...]:
    actions: list[ConfirmAction] = []
    for action_name in decision.acciones_ui:
        if action_name == "SHOW_ERROR":
            if decision.reason_code == "no_pending_rows":
                actions.append(ConfirmAction("SHOW_ERROR", reason_code=decision.reason_code, message=entrada.no_pending_message, title=entrada.no_pending_title))
            elif decision.reason_code == "conflictos_pendientes":
                actions.append(ConfirmAction("SHOW_ERROR", reason_code=decision.reason_code, message=entrada.conflict_message, title=entrada.conflict_title))
            else:
                actions.append(ConfirmAction("SHOW_ERROR", reason_code=decision.reason_code, message=decision.mensaje_usuario))
            continue
        actions.append(ConfirmAction(action_name, reason_code=decision.reason_code, message=decision.mensaje_usuario))
    return tuple(actions)


def build_confirmacion_plan(entrada: ConfirmacionEntrada) -> ConfirmacionPlan:
    decision = aplicar_reglas_confirmacion(entrada)
    return ConfirmacionPlan(decision=decision, actions=_actions_from_decision(decision, entrada))


def plan_confirmacion(entrada: ConfirmacionEntrada) -> list[ConfirmAction]:
    return list(build_confirmacion_plan(entrada).actions)
