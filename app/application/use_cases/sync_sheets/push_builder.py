from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.use_cases import sync_sheets_core


@dataclass(frozen=True)
class PushConflict:
    uuid_value: str
    local_row: dict[str, Any]
    remote_row: dict[str, Any]
    reason_code: str = "conflict_divergent"


@dataclass(frozen=True)
class PushBuildResult:
    values: tuple[tuple[Any, ...], ...]
    uploaded: int
    omitted_duplicates: int
    conflicts: tuple[PushConflict, ...]


def build_push_solicitudes_payloads(
    *,
    header: tuple[Any, ...],
    local_rows: list[Any],
    remote_rows: list[tuple[int, dict[str, Any]]],
    remote_index: dict[str, dict[str, Any]],
    last_sync_at: str | None,
    local_payload_builder: Any,
    remote_payload_builder: Any,
) -> PushBuildResult:
    values: list[tuple[Any, ...]] = [header]
    local_uuids: set[str] = set()
    uploaded = 0
    omitted_duplicates = 0
    conflicts: list[PushConflict] = []

    for row in local_rows:
        if last_sync_at and not sync_sheets_core.is_after_last_sync(row["updated_at"], last_sync_at):
            continue
        uuid_value = row["uuid"]
        local_uuids.add(uuid_value)
        remote_row = remote_index.get(uuid_value)
        remote_updated_at = sync_sheets_core.parse_iso(remote_row.get("updated_at") if remote_row else None)
        if sync_sheets_core.is_conflict(row["updated_at"], remote_updated_at, last_sync_at):
            conflicts.append(PushConflict(uuid_value=uuid_value, local_row=dict(row), remote_row=remote_row or {}))
            continue
        values.append(tuple(local_payload_builder(row)))
        uploaded += 1

    for _, remote_row in remote_rows:
        remote_uuid = str(remote_row.get("uuid", "")).strip()
        if not remote_uuid or remote_uuid in local_uuids:
            continue
        values.append(tuple(remote_payload_builder(remote_row)))
        omitted_duplicates += 1

    return PushBuildResult(
        values=tuple(values),
        uploaded=uploaded,
        omitted_duplicates=omitted_duplicates,
        conflicts=tuple(conflicts),
    )
