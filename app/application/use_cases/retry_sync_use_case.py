from __future__ import annotations

from dataclasses import dataclass

from app.domain.sync_models import SyncExecutionPlan, SyncPlanItem


@dataclass(frozen=True)
class RetryPlanResult:
    plan: SyncExecutionPlan
    retried_items: tuple[str, ...]


class RetrySyncUseCase:
    """Reconstruye un plan para reintentar solo elementos fallidos/conflictivos."""

    def build_retry_plan(
        self,
        base_plan: SyncExecutionPlan,
        *,
        item_status: dict[str, str],
    ) -> RetryPlanResult:
        retry_create = self._filter_items(base_plan.to_create, item_status)
        retry_update = self._filter_items(base_plan.to_update, item_status)
        unresolved_conflicts = tuple(
            item for item in base_plan.conflicts if item_status.get(item.uuid, "CONFLICT") == "CONFLICT"
        )
        retried = tuple(item.uuid for item in [*retry_create, *retry_update, *unresolved_conflicts])
        retry_plan = SyncExecutionPlan(
            generated_at=base_plan.generated_at,
            worksheet=base_plan.worksheet,
            to_create=retry_create,
            to_update=retry_update,
            unchanged=base_plan.unchanged,
            conflicts=unresolved_conflicts,
            potential_errors=base_plan.potential_errors,
            values_matrix=base_plan.values_matrix,
        )
        return RetryPlanResult(plan=retry_plan, retried_items=retried)

    @staticmethod
    def _filter_items(items: tuple[SyncPlanItem, ...], item_status: dict[str, str]) -> tuple[SyncPlanItem, ...]:
        return tuple(item for item in items if item_status.get(item.uuid, "ERROR") == "ERROR")
