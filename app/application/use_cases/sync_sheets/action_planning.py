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
    payload: dict[str, Any] = field(default_factory=dict)


# Planificador puro para que el caso de uso sea sólo orquestación.
def plan_pull_solicitud_action(
    *,
    has_uuid: bool,
    has_existing_for_empty_uuid: bool,
    has_local_uuid: bool,
    skip_duplicate: bool,
    conflict_detected: bool,
    remote_is_newer: bool,
    backfill_enabled: bool,
    existing_uuid: str | None,
) -> list[PullAction]:
    if not has_uuid:
        return _plan_without_uuid(has_existing_for_empty_uuid, backfill_enabled, existing_uuid)
    if not has_local_uuid:
        return _plan_insert_or_skip(skip_duplicate)
    return _plan_existing_uuid(conflict_detected, remote_is_newer)


def _plan_without_uuid(has_existing: bool, backfill_enabled: bool, existing_uuid: str | None) -> list[PullAction]:
    if not has_existing:
        return [PullAction("INSERT_SOLICITUD", {"uuid": None})]
    actions = [PullAction("SKIP", {"reason": "duplicate_without_uuid", "counter": "omitted_duplicates"})]
    if backfill_enabled and existing_uuid:
        actions.append(PullAction("BACKFILL_UUID", {"uuid": existing_uuid}))
    return actions


def _plan_insert_or_skip(skip_duplicate: bool) -> list[PullAction]:
    if skip_duplicate:
        return []
    return [PullAction("INSERT_SOLICITUD", {"uuid": "from_row"})]


def _plan_existing_uuid(conflict_detected: bool, remote_is_newer: bool) -> list[PullAction]:
    if conflict_detected:
        return [PullAction("REGISTER_CONFLICT")]
    if remote_is_newer:
        return [PullAction("UPDATE_SOLICITUD")]
    return []
