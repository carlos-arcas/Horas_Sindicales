from __future__ import annotations

from pathlib import Path

from app.application.use_cases.conflict_resolution_policy import ConflictResolutionPolicy
from app.application.use_cases.retry_sync_use_case import RetrySyncUseCase
from app.domain.sync_models import SyncExecutionPlan, SyncPlanItem


def _plan() -> SyncExecutionPlan:
    return SyncExecutionPlan(
        generated_at="2026-02-20T10:00:00",
        worksheet="solicitudes",
        to_create=(SyncPlanItem(uuid="ok-create", action="CREATE"), SyncPlanItem(uuid="err-create", action="CREATE")),
        to_update=(SyncPlanItem(uuid="ok-update", action="UPDATE"), SyncPlanItem(uuid="err-update", action="UPDATE")),
        unchanged=(SyncPlanItem(uuid="already-ok", action="NONE"),),
        conflicts=(SyncPlanItem(uuid="conf-1", action="CONFLICT", reason="fila modificada"),),
    )


def test_error_parcial_retry_only_processes_failures() -> None:
    use_case = RetrySyncUseCase()
    plan = _plan()

    result = use_case.build_retry_plan(
        plan,
        item_status={
            "ok-create": "OK",
            "err-create": "ERROR",
            "ok-update": "OK",
            "err-update": "ERROR",
            "conf-1": "CONFLICT",
        },
    )

    assert [item.uuid for item in result.plan.to_create] == ["err-create"]
    assert [item.uuid for item in result.plan.to_update] == ["err-update"]
    assert [item.uuid for item in result.plan.conflicts] == ["conf-1"]


def test_conflict_keep_local_moves_item_to_updates(tmp_path: Path) -> None:
    policy = ConflictResolutionPolicy(tmp_path)
    plan = _plan()

    adjusted, unresolved = policy.apply(plan, {"conf-1": "keep_local"})

    assert unresolved == ()
    assert "conf-1" in [item.uuid for item in adjusted.to_update]
    assert adjusted.conflicts == ()


def test_conflict_unresolved_blocks_final_sync() -> None:
    policy = ConflictResolutionPolicy(Path.cwd())
    adjusted, unresolved = policy.apply(_plan(), {})

    assert unresolved == ("conf-1",)
    assert [item.uuid for item in adjusted.conflicts] == ["conf-1"]


def test_double_retry_does_not_reprocess_ok_records() -> None:
    use_case = RetrySyncUseCase()
    plan = _plan()
    first_retry = use_case.build_retry_plan(
        plan,
        item_status={
            "ok-create": "OK",
            "err-create": "ERROR",
            "ok-update": "OK",
            "err-update": "ERROR",
            "conf-1": "CONFLICT",
        },
    ).plan

    second_retry = use_case.build_retry_plan(
        first_retry,
        item_status={
            "err-create": "OK",
            "err-update": "ERROR",
            "conf-1": "CONFLICT",
        },
    ).plan

    assert [item.uuid for item in second_retry.to_create] == []
    assert [item.uuid for item in second_retry.to_update] == ["err-update"]
