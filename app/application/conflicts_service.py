from __future__ import annotations

from datetime import datetime
from typing import Callable

from app.application.ports.conflicts_repository import ConflictRecord, ConflictsRepository


class ConflictsService:
    def __init__(
        self,
        repository: ConflictsRepository,
        device_id_provider: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._device_id_provider = device_id_provider or (lambda: "")

    def list_conflicts(self) -> list[ConflictRecord]:
        return self._repository.list_conflicts()

    def count_conflicts(self) -> int:
        return self._repository.count_conflicts()

    def resolve_conflict(self, conflict_id: int, keep: str) -> None:
        keep_local = keep.lower() == "local"
        self._repository.resolve_conflict(conflict_id, keep_local, self._device_id_provider())

    def resolve_all_latest(self) -> int:
        conflicts = self.list_conflicts()
        if not conflicts:
            return 0
        for conflict in conflicts:
            keep_local = self._is_local_newer(conflict.local_snapshot, conflict.remote_snapshot)
            self._repository.resolve_conflict(conflict.id, keep_local, self._device_id_provider())
        return len(conflicts)

    @staticmethod
    def _is_local_newer(local_snapshot: dict, remote_snapshot: dict) -> bool:
        local_updated = ConflictsService._parse_iso(local_snapshot.get("updated_at"))
        remote_updated = ConflictsService._parse_iso(remote_snapshot.get("updated_at"))
        if local_updated and remote_updated:
            return local_updated >= remote_updated
        if local_updated and not remote_updated:
            return True
        if remote_updated and not local_updated:
            return False
        return True

    @staticmethod
    def _parse_iso(value) -> datetime | None:
        if not value:
            return None
        try:
            text = str(value).replace("Z", "+00:00")
            return datetime.fromisoformat(text)
        except ValueError:
            return None
