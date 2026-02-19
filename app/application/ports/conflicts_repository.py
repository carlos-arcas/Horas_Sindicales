from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ConflictRecord:
    id: int
    uuid: str
    entity_type: str
    local_snapshot: dict
    remote_snapshot: dict
    detected_at: str


class ConflictsRepository(Protocol):
    def list_conflicts(self) -> list[ConflictRecord]:
        ...

    def count_conflicts(self) -> int:
        ...

    def resolve_conflict(self, conflict_id: int, keep_local: bool, device_id: str) -> bool:
        ...
