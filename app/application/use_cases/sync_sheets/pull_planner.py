from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PullCommand = Literal[
    "SKIP",
    "BACKFILL_UUID",
    "INSERT_SOLICITUD",
    "UPDATE_SOLICITUD",
    "REGISTER_CONFLICT",
]


@dataclass(frozen=True)
class PullAction:
    command: PullCommand
    reason_code: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PullPlannerSignals:
    has_uuid: bool
    has_existing_for_empty_uuid: bool
    has_local_uuid: bool
    skip_duplicate: bool
    conflict_detected: bool
    remote_is_newer: bool
    backfill_enabled: bool
    existing_uuid: str | None


def plan_pull_actions(signals: PullPlannerSignals) -> tuple[PullAction, ...]:
    if not signals.has_uuid:
        return _plan_without_uuid(signals)
    if not signals.has_local_uuid:
        if signals.skip_duplicate:
            return (PullAction("SKIP", "duplicate_with_uuid"),)
        return (PullAction("INSERT_SOLICITUD", "insert_new_uuid", {"uuid": "from_row"}),)
    if signals.conflict_detected:
        return (PullAction("REGISTER_CONFLICT", "conflict_divergent"),)
    if signals.remote_is_newer:
        return (PullAction("UPDATE_SOLICITUD", "remote_newer"),)
    return (PullAction("SKIP", "local_is_newer_or_equal"),)


def _plan_without_uuid(signals: PullPlannerSignals) -> tuple[PullAction, ...]:
    if not signals.has_existing_for_empty_uuid:
        return (PullAction("INSERT_SOLICITUD", "insert_missing_uuid", {"uuid": None}),)

    actions: list[PullAction] = [
        PullAction("SKIP", "duplicate_without_uuid", {"counter": "omitted_duplicates"})
    ]
    if signals.backfill_enabled and signals.existing_uuid:
        actions.append(PullAction("BACKFILL_UUID", "backfill_existing_uuid", {"uuid": signals.existing_uuid}))
    return tuple(actions)
