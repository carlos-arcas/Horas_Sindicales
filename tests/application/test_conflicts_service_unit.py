from __future__ import annotations

from app.application.conflicts_service import ConflictRecord, ConflictsService


class FakeConflictsRepository:
    def __init__(self, conflicts: list[ConflictRecord] | None = None) -> None:
        self.conflicts = conflicts or []
        self.calls: list[tuple[int, bool, str]] = []

    def list_conflicts(self) -> list[ConflictRecord]:
        return list(self.conflicts)

    def count_conflicts(self) -> int:
        return len(self.conflicts)

    def resolve_conflict(self, conflict_id: int, keep_local: bool, device_id: str) -> bool:
        self.calls.append((conflict_id, keep_local, device_id))
        return True


def test_conflicts_service_uses_policy_for_latest_resolution() -> None:
    repo = FakeConflictsRepository(
        conflicts=[
            ConflictRecord(
                id=1,
                uuid="a",
                entity_type="delegadas",
                local_snapshot={"updated_at": "2025-01-01T10:00:00Z"},
                remote_snapshot={"updated_at": "2025-01-01T09:00:00Z"},
                detected_at="2025-01-01T12:00:00Z",
            ),
            ConflictRecord(
                id=2,
                uuid="b",
                entity_type="delegadas",
                local_snapshot={"updated_at": "2025-01-01T08:00:00Z"},
                remote_snapshot={"updated_at": "2025-01-01T09:00:00Z"},
                detected_at="2025-01-01T12:01:00Z",
            ),
        ]
    )
    service = ConflictsService(repo, device_id_provider=lambda: "device-1")

    resolved = service.resolve_all_latest()

    assert resolved == 2
    assert repo.calls == [(1, True, "device-1"), (2, False, "device-1")]


def test_conflicts_service_resolve_conflict_maps_keep_option() -> None:
    repo = FakeConflictsRepository()
    service = ConflictsService(repo, device_id_provider=lambda: "device-2")

    service.resolve_conflict(7, "remote")

    assert repo.calls == [(7, False, "device-2")]
