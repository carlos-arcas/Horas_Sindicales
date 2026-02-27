from __future__ import annotations

import sqlite3

import pytest

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.domain.models import SheetsConfig
from app.infrastructure.migrations import run_migrations
from tests.e2e_sync.fakes import FakeSheetsConfigStore, FakeSheetsGateway, FakeSheetsRepository


@pytest.fixture
def e2e_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def make_service(e2e_connection: sqlite3.Connection):
    def _factory(
        *,
        initial_values: dict[str, list[list[object]]] | None = None,
        rate_limit_failures: dict[str, int] | None = None,
    ) -> tuple[SheetsSyncService, FakeSheetsGateway]:
        fake_gateway = FakeSheetsGateway(
            initial_values=initial_values,
            rate_limit_failures=rate_limit_failures,
        )
        config_store = FakeSheetsConfigStore(
            SheetsConfig(
                spreadsheet_id="sheet-e2e",
                credentials_path="/tmp/fake-credentials.json",
                device_id="device-e2e",
            )
        )
        service = SheetsSyncService(
            connection=e2e_connection,
            config_store=config_store,
            client=fake_gateway,
            repository=FakeSheetsRepository(),
        )
        return service, fake_gateway

    return _factory
