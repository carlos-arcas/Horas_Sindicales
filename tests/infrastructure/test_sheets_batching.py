from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import gspread
import pytest

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.core.metrics import MetricsRegistry
from app.domain.models import SheetsConfig
from app.infrastructure import sheets_client as sheets_client_module
from app.infrastructure.sheets_client import SheetsClient


@dataclass
class _FakeConfigStore:
    config: SheetsConfig | None

    def load(self) -> SheetsConfig | None:
        return self.config


class _FakeRepository:
    def ensure_schema(self, _spreadsheet, _schema):
        return []


class _FakeWorksheet:
    def __init__(self, title: str, values: list[list[str]] | None = None) -> None:
        self.title = title
        self._values = values or []

    def get_all_values(self) -> list[list[str]]:
        return self._values


class _Resp429:
    status_code = 429
    text = "RESOURCE_EXHAUSTED"


def _build_service(connection, client) -> SheetsSyncService:
    return SheetsSyncService(
        connection=connection,
        config_store=_FakeConfigStore(SheetsConfig("sheet-id", "/tmp/creds.json", "device")),
        client=client,
        repository=_FakeRepository(),
    )


def test_multiple_rows_flush_to_single_values_batch_update(connection) -> None:
    worksheet = _FakeWorksheet("delegadas", [["uuid", "nombre"]])
    client = SimpleNamespace(
        values_batch_update=Mock(),
        read_all_values=Mock(return_value=[["uuid", "nombre"]]),
    )
    service = _build_service(connection, client)

    service._pending_append_rows[worksheet.title] = [["u1", "A"], ["u2", "B"]]
    service._flush_write_batches(SimpleNamespace(values_batch_update=Mock()), worksheet)

    client.values_batch_update.assert_called_once_with(
        {
            "valueInputOption": "USER_ENTERED",
            "data": [{"range": "'delegadas'!A2:B3", "values": [["u1", "A"], ["u2", "B"]]}],
        }
    )


def test_cache_avoids_duplicate_worksheet_fetch() -> None:
    worksheet = _FakeWorksheet("delegadas")
    spreadsheet = SimpleNamespace(
        worksheet=Mock(return_value=worksheet),
        worksheets=Mock(return_value=[worksheet]),
    )
    client = SheetsClient()
    client._spreadsheet = spreadsheet

    by_title = client.get_worksheets_by_title()
    fetched = client.get_worksheet("delegadas")

    assert by_title["delegadas"] is worksheet
    assert fetched is worksheet
    spreadsheet.worksheets.assert_called_once()
    spreadsheet.worksheet.assert_not_called()


def test_sheets_api_calls_counter_tracks_real_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = MetricsRegistry()
    monkeypatch.setattr(sheets_client_module, "metrics_registry", registry)

    worksheet = _FakeWorksheet("delegadas", [["uuid"], ["1"]])
    spreadsheet = SimpleNamespace(
        worksheet=Mock(return_value=worksheet),
        worksheets=Mock(return_value=[worksheet]),
    )
    client = SheetsClient()
    client._spreadsheet = spreadsheet

    client.get_worksheet("delegadas")
    client.read_all_values("delegadas")
    client.get_worksheet("delegadas")
    client.get_worksheets_by_title()
    client.get_worksheets_by_title()

    assert client.get_sheets_api_calls_count() == 3
    assert client.get_avoided_requests_count() >= 2
    assert registry.contador("sheets_api_calls") == 3


def test_retry_counts_each_real_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = MetricsRegistry()
    monkeypatch.setattr(sheets_client_module, "metrics_registry", registry)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    client = SheetsClient()
    attempts = {"count": 0}

    def flaky_operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise gspread.exceptions.APIError(_Resp429())
        return "ok"

    assert client._with_write_retry("spreadsheet.values_batch_update", flaky_operation) == "ok"
    assert attempts["count"] == 3
    assert client.get_sheets_api_calls_count() == 3
    assert registry.contador("sheets_api_calls") == 3
