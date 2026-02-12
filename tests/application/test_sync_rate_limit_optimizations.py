from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.domain.models import SheetsConfig


@dataclass
class _FakeConfigStore:
    config: SheetsConfig

    def load(self) -> SheetsConfig:
        return self.config


class _FakeWorksheet:
    def __init__(self, title: str, values: list[list[str]]) -> None:
        self.title = title
        self._values = values
        self.get_all_values_calls = 0

    def get_all_values(self) -> list[list[str]]:
        self.get_all_values_calls += 1
        return self._values


class _FakeSpreadsheet:
    def __init__(self, worksheets: dict[str, _FakeWorksheet]) -> None:
        self._worksheets = worksheets
        self.worksheet_calls = 0

    def worksheet(self, name: str) -> _FakeWorksheet:
        self.worksheet_calls += 1
        return self._worksheets[name]


class _FakeClient:
    def __init__(self, spreadsheet: _FakeSpreadsheet) -> None:
        self.spreadsheet = spreadsheet
        self.open_calls = 0

    def open_spreadsheet(self, _: Path, __: str) -> _FakeSpreadsheet:
        self.open_calls += 1
        return self.spreadsheet


class _FakeRepository:
    def ensure_schema(self, *_args, **_kwargs):
        return []


def _sheet(headers: list[str]) -> list[list[str]]:
    return [headers]


def test_sync_bidirectional_reuses_open_spreadsheet(connection) -> None:
    worksheets = {
        "delegadas": _FakeWorksheet("delegadas", _sheet(["uuid", "updated_at"])),
        "solicitudes": _FakeWorksheet("solicitudes", _sheet(["uuid", "updated_at"])),
        "cuadrantes": _FakeWorksheet("cuadrantes", _sheet(["uuid", "updated_at"])),
        "pdf_log": _FakeWorksheet("pdf_log", _sheet(["pdf_id", "updated_at"])),
        "config": _FakeWorksheet("config", _sheet(["key", "updated_at"])),
    }
    spreadsheet = _FakeSpreadsheet(worksheets)
    fake_client = _FakeClient(spreadsheet)

    service = SheetsSyncService(
        connection=connection,
        config_store=_FakeConfigStore(
            SheetsConfig(
                spreadsheet_id="sheet-id",
                credentials_path="/tmp/fake_credentials.json",
                device_id="device-local",
            )
        ),
        client=fake_client,
        repository=_FakeRepository(),
    )

    service.sync_bidirectional()

    assert fake_client.open_calls == 1
