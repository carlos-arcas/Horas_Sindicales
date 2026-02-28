from __future__ import annotations

from datetime import datetime, timezone

from app.application.use_cases.sync_sheets import conflict_policy
from app.application.use_cases.sync_sheets.helpers import _build_solicitud_plan_for_local_row


class _ContractFakeService:
    def _is_after_last_sync(self, updated: str | None, last_sync: str) -> bool:
        return bool(updated and updated > last_sync)

    def _parse_iso(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _is_conflict(self, local_updated: str | None, remote_updated: datetime | None, last_sync: str | None) -> bool:
        return conflict_policy.is_conflict(local_updated, remote_updated, last_sync)

    def _local_solicitud_payload(self, row):
        return (row["uuid"], row["updated_at"], row["notas"])

    def _remote_solicitud_payload(self, row):
        return (row.get("uuid"), row.get("updated_at"), row.get("raw"))


def test_evaluate_conflict_policy_detects_divergent_conflict() -> None:
    decision = conflict_policy.evaluate_conflict_policy(
        local_updated_at="2026-01-03T10:00:00+00:00",
        remote_updated_at=datetime(2026, 1, 3, 11, 0, tzinfo=timezone.utc),
        last_sync_at="2026-01-02T00:00:00+00:00",
    )

    assert decision.outcome is conflict_policy.ConflictOutcome.DIVERGENT_CONFLICT
    assert decision.allow_overwrite_local is False
    assert decision.should_register_conflict is True
    assert conflict_policy.is_conflict(
        "2026-01-03T10:00:00+00:00",
        datetime(2026, 1, 3, 11, 0, tzinfo=timezone.utc),
        "2026-01-02T00:00:00+00:00",
    ) is True


def test_evaluate_conflict_policy_allows_overwrite_when_missing_remote_update() -> None:
    decision = conflict_policy.evaluate_conflict_policy(
        local_updated_at="2026-01-03T10:00:00+00:00",
        remote_updated_at=None,
        last_sync_at="2026-01-02T00:00:00+00:00",
    )

    assert decision.outcome is conflict_policy.ConflictOutcome.NO_CONFLICT
    assert decision.allow_overwrite_local is True
    assert decision.should_register_conflict is False


def test_evaluate_conflict_policy_allows_overwrite_with_invalid_timestamps() -> None:
    decision = conflict_policy.evaluate_conflict_policy(
        local_updated_at="fecha-invalida",
        remote_updated_at=datetime(2026, 1, 3, 11, 0, tzinfo=timezone.utc),
        last_sync_at="2026-01-02T00:00:00+00:00",
    )

    assert decision.outcome is conflict_policy.ConflictOutcome.NO_CONFLICT
    assert decision.allow_overwrite_local is True
    assert decision.should_register_conflict is False


def test_contract_conflicto_divergente_returns_conflict_and_does_not_enqueue_payload() -> None:
    service = _ContractFakeService()
    values: list[tuple[object, ...]] = []
    errors: list[str] = []
    row = {"uuid": "u-1", "updated_at": "2026-01-06T10:00:00+00:00", "notas": "local"}
    remote_index = {"u-1": {"uuid": "u-1", "updated_at": "2026-01-06T11:00:00+00:00", "raw": "remote"}}

    action = _build_solicitud_plan_for_local_row(
        service,
        row,
        remote_index,
        "2026-01-05T00:00:00+00:00",
        ["uuid", "updated_at", "raw"],
        values,
        errors,
    )

    assert action is not None
    assert action.action == "conflict"
    assert values == []
    assert errors == []


def test_contract_non_conflict_allows_update_path() -> None:
    service = _ContractFakeService()
    values: list[tuple[object, ...]] = []
    errors: list[str] = []
    row = {"uuid": "u-1", "updated_at": "2026-01-04T10:00:00+00:00", "notas": "local-new"}
    remote_index = {"u-1": {"uuid": "u-1", "updated_at": "2025-12-31T23:00:00+00:00", "raw": "remote-old"}}

    action = _build_solicitud_plan_for_local_row(
        service,
        row,
        remote_index,
        "2026-01-01T00:00:00+00:00",
        ["uuid", "updated_at", "raw"],
        values,
        errors,
    )

    assert action is not None
    assert action.action == "update"
    assert values == [("u-1", "2026-01-04T10:00:00+00:00", "local-new")]
    assert errors == []
