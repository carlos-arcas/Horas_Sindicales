from __future__ import annotations

from pathlib import Path
from typing import Any

from app.application.sheets_service import SHEETS_SCHEMA
from app.domain.models import SheetsConfig
from app.domain.ports import SheetsGatewayPort
from app.infrastructure.sheets_client import SheetsClient
from app.infrastructure.sheets_gateway_puros import (
    ensure_headers,
    ensure_uuid_header,
    find_uuid_row,
    map_gateway_error,
    merge_values_for_upsert,
    normalize_rows,
)
from app.infrastructure.sheets_repository import SheetsRepository


class SheetsGatewayGspread(SheetsGatewayPort):
    def __init__(self, client: SheetsClient, repository: SheetsRepository) -> None:
        self._client = client
        self._repository = repository

    def test_connection(self, config: SheetsConfig, schema: dict[str, list[str]]) -> tuple[str, str, list[str]]:
        spreadsheet = self._open(config)
        actions = self._repository.ensure_schema(spreadsheet, schema)
        return spreadsheet.title, spreadsheet.id, actions

    def read_personas(self, config: SheetsConfig) -> list[tuple[int, dict[str, Any]]]:
        return self._read_rows(config, "delegadas")

    def read_solicitudes(self, config: SheetsConfig) -> list[tuple[int, dict[str, Any]]]:
        return self._read_rows(config, "solicitudes")

    def upsert_persona(self, config: SheetsConfig, row: dict[str, Any]) -> None:
        self._upsert_row(config, "delegadas", row)

    def upsert_solicitud(self, config: SheetsConfig, row: dict[str, Any]) -> None:
        self._upsert_row(config, "solicitudes", row)

    def backfill_uuid(self, config: SheetsConfig, worksheet_name: str, row_index: int, uuid_value: str) -> None:
        try:
            spreadsheet = self._open(config)
            worksheet = spreadsheet.worksheet(worksheet_name)
            headers, created_header = ensure_uuid_header(worksheet.row_values(1))
            if created_header:
                worksheet.update("A1", [headers])
            worksheet.update_cell(row_index, headers.index("uuid") + 1, uuid_value)
        except Exception as exc:  # noqa: BLE001
            raise map_gateway_error(exc) from exc

    def _open(self, config: SheetsConfig):
        try:
            spreadsheet = self._client.open_spreadsheet(Path(config.credentials_path), config.spreadsheet_id)
            self._repository.ensure_schema(spreadsheet, SHEETS_SCHEMA)
            return spreadsheet
        except Exception as exc:  # noqa: BLE001
            raise map_gateway_error(exc) from exc

    def _read_rows(self, config: SheetsConfig, worksheet_name: str) -> list[tuple[int, dict[str, Any]]]:
        try:
            worksheet = self._open(config).worksheet(worksheet_name)
            return normalize_rows(worksheet.get_all_values())
        except Exception as exc:  # noqa: BLE001
            raise map_gateway_error(exc) from exc

    def _upsert_row(self, config: SheetsConfig, worksheet_name: str, row: dict[str, Any]) -> None:
        try:
            worksheet = self._open(config).worksheet(worksheet_name)
            current_headers = worksheet.row_values(1)
            headers = ensure_headers(current_headers, row)
            if not current_headers:
                worksheet.update("A1", [headers])
            records = worksheet.get_all_records()
            row_idx = find_uuid_row(records, str(row.get("uuid", "")))
            if row_idx is not None:
                record = records[row_idx - 2]
                worksheet.update(f"A{row_idx}", [merge_values_for_upsert(headers, row, record)])
                return
            worksheet.append_row(merge_values_for_upsert(headers, row), value_input_option="USER_ENTERED")
        except Exception as exc:  # noqa: BLE001
            raise map_gateway_error(exc) from exc
