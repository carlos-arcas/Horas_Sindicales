from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IterActionType = Literal["APPEND_PENDING"]


@dataclass(frozen=True)
class PendienteRowSnapshot:
    row: int
    solicitud_id: int | None
    persona_id: int | None
    fecha_raw: object
    desde_raw: object
    hasta_raw: object
    delegada_raw: object


@dataclass(frozen=True)
class IterPendientesEntrada:
    ui_ready: bool
    rows: tuple[PendienteRowSnapshot, ...]


@dataclass(frozen=True)
class IterAction:
    action_type: IterActionType
    reason_code: str
    payload: dict[str, object]


@dataclass(frozen=True)
class IterPlan:
    reason_code: str
    actions: tuple[IterAction, ...]


def _normalize_time_cell(value: object) -> str:
    return "" if value in (None, "-") else str(value)


def _normalize_delegada_cell(value: object) -> object:
    return None if value in (None, "-") else value


def _build_pending_payload(snapshot: PendienteRowSnapshot) -> dict[str, object]:
    return {
        "row": snapshot.row,
        "id": snapshot.solicitud_id,
        "fecha": _normalize_time_cell(snapshot.fecha_raw),
        "desde": _normalize_time_cell(snapshot.desde_raw),
        "hasta": _normalize_time_cell(snapshot.hasta_raw),
        "persona_id": snapshot.persona_id,
        "delegada": _normalize_delegada_cell(snapshot.delegada_raw),
    }


def _plan_row(snapshot: PendienteRowSnapshot) -> IterAction | None:
    if snapshot.row < 0:
        return None
    return IterAction(
        action_type="APPEND_PENDING",
        reason_code="row_included",
        payload=_build_pending_payload(snapshot),
    )


def plan_iter_pendientes(entrada: IterPendientesEntrada) -> IterPlan:
    if not entrada.ui_ready:
        return IterPlan(reason_code="ui_not_ready", actions=())

    actions: list[IterAction] = []
    for snapshot in entrada.rows:
        action = _plan_row(snapshot)
        if action is None:
            continue
        actions.append(action)

    if not actions:
        return IterPlan(reason_code="no_rows_to_iterate", actions=())
    return IterPlan(reason_code="rows_planned", actions=tuple(actions))
