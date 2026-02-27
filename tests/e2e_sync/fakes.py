from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.application.sheets_service import SHEETS_SCHEMA
from app.domain.models import SheetsConfig
from app.domain.sheets_errors import SheetsRateLimitError


@dataclass
class FakeSheetsConfigStore:
    config: SheetsConfig

    def load(self) -> SheetsConfig | None:
        return self.config


class FakeSheetsRepository:
    def ensure_schema(self, *_: Any, **__: Any) -> list[str]:
        return []


class FakeWorksheet:
    def __init__(self, title: str, values_ref: list[list[Any]]) -> None:
        self.title = title
        self._values_ref = values_ref

    def update(self, cell: str, values: list[list[Any]]) -> None:
        if cell == "A1":
            self._values_ref[:] = values

    def resize(self, cols: int | None = None) -> None:
        return None

    def append_rows(self, rows: list[list[Any]], value_input_option: str | None = None) -> None:
        self._values_ref.extend(rows)

    def batch_update(self, data: list[dict[str, Any]], value_input_option: str | None = None) -> None:
        return None


class FakeSheetsGateway:
    """Fake explícito para tests E2E del sincronizador sin red ni gspread real."""

    def __init__(
        self,
        *,
        initial_values: dict[str, list[list[Any]]] | None = None,
        fail_on_operation: Exception | None = None,
        rate_limit_failures: dict[str, int] | None = None,
    ) -> None:
        self._values: dict[str, list[list[Any]]] = {}
        for worksheet_name, headers in SHEETS_SCHEMA.items():
            self._values[worksheet_name] = [headers]
        if initial_values:
            for name, rows in initial_values.items():
                self._values[name] = rows
        self._fail_on_operation = fail_on_operation
        self._rate_limit_remaining = dict(rate_limit_failures or {})
        self._worksheets = {name: FakeWorksheet(name, self._values[name]) for name in self._values}
        self.read_calls_count = 0
        self.write_calls_count = 0
        self.rate_limit_retries = 0

    def open_spreadsheet(self, credentials_path: Path, spreadsheet_id: str) -> object:
        if self._fail_on_operation is not None:
            raise self._fail_on_operation
        return object()

    def read_all_values(self, worksheet_name: str) -> list[list[Any]]:
        self.read_calls_count += 1
        remaining = self._rate_limit_remaining.get(worksheet_name, 0)
        if remaining > 0:
            self._rate_limit_remaining[worksheet_name] = remaining - 1
            self.rate_limit_retries += 1
            raise SheetsRateLimitError(f"Rate limit simulado en {worksheet_name}")
        return self._values.get(worksheet_name, [[]])

    def get_worksheet(self, name: str) -> FakeWorksheet:
        return self._worksheets[name]

    def get_worksheets_by_title(self) -> dict[str, FakeWorksheet]:
        return self._worksheets

    def batch_get_ranges(self, ranges: list[str]) -> dict[str, list[list[str]]]:
        return {rng: [] for rng in ranges}

    def get_read_calls_count(self) -> int:
        return self.read_calls_count

    def get_avoided_requests_count(self) -> int:
        return 0

    def get_write_calls_count(self) -> int:
        return self.write_calls_count

    def append_rows(self, worksheet_name: str, rows: list[list[Any]]) -> None:
        self.write_calls_count += 1
        if worksheet_name not in self._values:
            self._values[worksheet_name] = [[]]
        self._values[worksheet_name].extend(rows)

    def batch_update(self, worksheet_name: str, data: list[dict[str, Any]]) -> None:
        self.write_calls_count += 1

    def values_batch_update(self, body: dict[str, Any]) -> None:
        self.write_calls_count += 1
