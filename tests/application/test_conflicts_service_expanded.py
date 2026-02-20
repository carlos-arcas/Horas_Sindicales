from __future__ import annotations

from app.application.conflicts_service import ConflictsService


class _Repo:
    def __init__(self) -> None:
        self.calls: list[tuple[int, bool, str]] = []

    def list_conflicts(self):
        return []

    def count_conflicts(self) -> int:
        return 0

    def resolve_conflict(self, conflict_id: int, keep_local: bool, device_id: str) -> bool:
        self.calls.append((conflict_id, keep_local, device_id))
        return True


def test_resolve_all_latest_returns_zero_without_conflicts() -> None:
    service = ConflictsService(_Repo(), device_id_provider=lambda: "dev-0")
    assert service.resolve_all_latest() == 0


def test_is_local_newer_defaults_to_local_when_timestamps_missing() -> None:
    assert ConflictsService._is_local_newer({}, {}) is True
    assert ConflictsService._is_local_newer({"updated_at": "invalid"}, {"updated_at": "also-invalid"}) is True


def test_parse_iso_returns_none_for_empty_values() -> None:
    assert ConflictsService._parse_iso(None) is None
    assert ConflictsService._parse_iso("") is None
