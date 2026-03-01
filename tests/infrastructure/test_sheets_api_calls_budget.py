from __future__ import annotations

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.domain.models import SheetsConfig
from tests.e2e_sync.fakes import FakeSheetsConfigStore, FakeSheetsGateway, FakeSheetsRepository


class _BudgetAwareFakeSheetsGateway(FakeSheetsGateway):
    def get_sheets_api_calls_count(self) -> int:
        return self.read_calls_count + self.write_calls_count


def test_sync_bidirectional_keeps_sheets_api_calls_within_budget(connection) -> None:
    gateway = _BudgetAwareFakeSheetsGateway()
    service = SheetsSyncService(
        connection=connection,
        config_store=FakeSheetsConfigStore(
            SheetsConfig(
                spreadsheet_id="sheet-budget",
                credentials_path="/tmp/fake-credentials.json",
                device_id="device-ci",
            )
        ),
        client=gateway,
        repository=FakeSheetsRepository(),
    )

    service.sync_bidirectional()

    sheets_api_calls_count = gateway.get_sheets_api_calls_count()
    assert sheets_api_calls_count <= 10
