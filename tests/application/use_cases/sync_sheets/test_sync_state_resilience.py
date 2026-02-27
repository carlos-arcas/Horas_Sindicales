from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from unittest.mock import Mock

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.domain.models import SheetsConfig


@dataclass
class _FakeConfigStore:
    config: SheetsConfig | None

    def load(self) -> SheetsConfig | None:
        return self.config


class _FakeClient:
    def __init__(self) -> None:
        self.open_spreadsheet = Mock()


class _FakeRepository:
    def ensure_schema(self, spreadsheet, schema) -> list[str]:
        return []


def test_get_last_sync_at_returns_none_when_sync_state_table_is_missing() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    service = SheetsSyncService(
        connection=connection,
        config_store=_FakeConfigStore(SheetsConfig("sheet-id", "/tmp/creds.json", "device-test")),
        client=_FakeClient(),
        repository=_FakeRepository(),
    )

    try:
        result = service.get_last_sync_at()

        assert result is None
        row = connection.execute("SELECT last_sync_at FROM sync_state WHERE id = 1").fetchone()
        assert row is not None
        assert row["last_sync_at"] is None
    finally:
        connection.close()
