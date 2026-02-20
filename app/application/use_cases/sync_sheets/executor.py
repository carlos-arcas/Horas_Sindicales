from __future__ import annotations

from typing import Any

from app.domain.sync_models import SyncExecutionPlan, SyncSummary


def execute_plan(service: Any, spreadsheet: Any, plan: SyncExecutionPlan) -> SyncSummary:
    worksheet = service._get_worksheet(spreadsheet, plan.worksheet)
    values = [list(row) for row in plan.values_matrix]
    worksheet.update("A1", values)
    service._set_last_sync_at(service._now_iso())
    service._log_sync_stats("execute_sync_plan")
    return SyncSummary(
        inserted_remote=len(plan.to_create),
        updated_remote=len(plan.to_update),
        duplicates_skipped=len(plan.unchanged),
        conflicts_detected=len(plan.conflicts),
        errors=len(plan.potential_errors),
    )
