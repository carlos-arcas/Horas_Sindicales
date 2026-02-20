from unittest.mock import Mock

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.domain.sync_models import SyncExecutionPlan, SyncPlanItem


def test_execute_sync_plan_keeps_expected_summary_shape() -> None:
    repository = Mock()
    service = SheetsSyncService(
        connection=Mock(),
        config_store=Mock(),
        client=Mock(),
        repository=repository,
    )

    worksheet = Mock()
    service._open_spreadsheet = Mock(return_value=object())
    service._prepare_sync_context = Mock()
    service._get_worksheet = Mock(return_value=worksheet)
    service._set_last_sync_at = Mock()
    service._now_iso = Mock(return_value="2026-01-01T00:00:00Z")
    service._log_sync_stats = Mock()

    plan = SyncExecutionPlan(
        generated_at="2026-01-01T00:00:00Z",
        worksheet="solicitudes",
        to_create=(SyncPlanItem(uuid="a", action="create"),),
        to_update=(SyncPlanItem(uuid="b", action="update"), SyncPlanItem(uuid="c", action="update")),
        unchanged=(SyncPlanItem(uuid="d", action="none"),),
        conflicts=(SyncPlanItem(uuid="e", action="conflict"),),
        potential_errors=("error",),
        values_matrix=(("h1",), ("v1",)),
    )

    summary = service.execute_sync_plan(plan)

    assert summary.inserted_remote == 1
    assert summary.updated_remote == 2
    assert summary.duplicates_skipped == 1
    assert summary.conflicts_detected == 1
    assert summary.errors == 1
