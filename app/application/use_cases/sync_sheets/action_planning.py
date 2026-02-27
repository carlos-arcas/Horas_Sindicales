from __future__ import annotations

from typing import Literal

PullAction = Literal[
    "backfill_without_uuid",
    "insert_without_uuid",
    "skip_without_uuid",
    "insert_with_uuid",
    "skip_duplicate",
    "store_conflict",
    "update_local",
    "noop",
]


# Planificador puro para que el caso de uso sea sólo orquestación.
def plan_pull_solicitud_action(
    *,
    has_uuid: bool,
    has_existing_for_empty_uuid: bool,
    has_local_uuid: bool,
    skip_duplicate: bool,
    conflict_detected: bool,
    remote_is_newer: bool,
) -> PullAction:
    if not has_uuid:
        if has_existing_for_empty_uuid:
            return "backfill_without_uuid"
        return "insert_without_uuid"
    if not has_local_uuid:
        if skip_duplicate:
            return "skip_duplicate"
        return "insert_with_uuid"
    if conflict_detected:
        return "store_conflict"
    if remote_is_newer:
        return "update_local"
    return "noop"
