from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.domain.sync_models import SyncExecutionPlan, SyncPlanItem, SyncSummary


class _FakeSyncPort:
    def __init__(self) -> None:
        self.writes = 0
        self._plan = SyncExecutionPlan(
            generated_at="2026-01-01T00:00:00",
            worksheet="solicitudes",
            to_create=(SyncPlanItem(uuid="a", action="create", reason="Nuevo registro"),),
            to_update=(SyncPlanItem(uuid="b", action="update"),),
            unchanged=(SyncPlanItem(uuid="c", action="unchanged"),),
            conflicts=(),
            potential_errors=(),
            values_matrix=(("uuid",), ("a",), ("b",), ("c",)),
        )

    def pull(self) -> SyncSummary:
        return SyncSummary()

    def push(self) -> SyncSummary:
        return SyncSummary()

    def sync(self) -> SyncSummary:
        return self.sync_bidirectional()

    def sync_bidirectional(self) -> SyncSummary:
        if self.writes == 0:
            self.writes += 1
            return SyncSummary(inserted_remote=1, updated_remote=1)
        return SyncSummary()

    def simulate_sync_plan(self) -> SyncExecutionPlan:
        return self._plan

    def execute_sync_plan(self, plan: SyncExecutionPlan) -> SyncSummary:
        assert plan == self._plan
        self.writes += 1
        return SyncSummary(inserted_remote=len(plan.to_create), updated_remote=len(plan.to_update))

    def get_last_sync_at(self) -> str | None:
        return None

    def is_configured(self) -> bool:
        return True

    def store_sync_config_value(self, key: str, value: str) -> None:
        return None

    def register_pdf_log(self, persona_id: int, fechas: list[str], pdf_hash: str | None) -> None:
        return None


def test_dry_run_does_not_write() -> None:
    fake = _FakeSyncPort()
    use_case = SyncSheetsUseCase(fake)

    plan = use_case.simulate_sync_plan()

    assert plan.has_changes is True
    assert fake.writes == 0


def test_simulated_plan_execution_matches_direct_sync_result() -> None:
    fake = _FakeSyncPort()
    use_case = SyncSheetsUseCase(fake)

    planned = use_case.execute_sync_plan(use_case.simulate_sync_plan())

    fake_direct = _FakeSyncPort()
    direct = SyncSheetsUseCase(fake_direct).sync_bidirectional()

    assert planned.inserted_remote == direct.inserted_remote
    assert planned.updated_remote == direct.updated_remote


def test_second_execution_is_idempotent() -> None:
    fake = _FakeSyncPort()
    use_case = SyncSheetsUseCase(fake)

    first = use_case.sync_bidirectional()
    second = use_case.sync_bidirectional()

    assert first.inserted_remote > 0
    assert first.updated_remote > 0
    assert second.inserted_remote == 0
    assert second.updated_remote == 0
