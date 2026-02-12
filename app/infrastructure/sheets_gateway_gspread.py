from __future__ import annotations

from pathlib import Path
from typing import Any

from app.application.sheets_service import SHEETS_SCHEMA
from app.domain.models import SheetsConfig
from app.domain.ports import SheetsGatewayPort
from app.infrastructure.sheets_client import SheetsClient
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
        spreadsheet = self._open(config)
        worksheet = spreadsheet.worksheet(worksheet_name)
        headers = worksheet.row_values(1)
        if "uuid" not in headers:
            headers = [*headers, "uuid"]
            worksheet.update("A1", [headers])
        col = headers.index("uuid") + 1
        worksheet.update_cell(row_index, col, uuid_value)

    def _open(self, config: SheetsConfig):
        spreadsheet = self._client.open_spreadsheet(Path(config.credentials_path), config.spreadsheet_id)
        self._repository.ensure_schema(spreadsheet, SHEETS_SCHEMA)
        return spreadsheet

    def _read_rows(self, config: SheetsConfig, worksheet_name: str) -> list[tuple[int, dict[str, Any]]]:
        worksheet = self._open(config).worksheet(worksheet_name)
        values = worksheet.get_all_values()
        if not values:
            return []
        headers = values[0]
        rows: list[tuple[int, dict[str, Any]]] = []
        for row_number, row in enumerate(values[1:], start=2):
            payload = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            if any(str(v).strip() for v in payload.values()):
                rows.append((row_number, payload))
        return rows

    def _upsert_row(self, config: SheetsConfig, worksheet_name: str, row: dict[str, Any]) -> None:
        worksheet = self._open(config).worksheet(worksheet_name)
        headers = worksheet.row_values(1)
        if not headers:
            headers = list(row.keys())
            worksheet.update("A1", [headers])
        uuid_value = str(row.get("uuid", "")).strip()
        records = worksheet.get_all_records()
        for idx, record in enumerate(records, start=2):
            if str(record.get("uuid", "")).strip() == uuid_value and uuid_value:
                values = [row.get(h, record.get(h, "")) for h in headers]
                worksheet.update(f"A{idx}", [values])
                return
        worksheet.append_row([row.get(h, "") for h in headers], value_input_option="USER_ENTERED")
