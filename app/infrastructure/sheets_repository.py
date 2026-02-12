from __future__ import annotations

import logging
from typing import Iterable

import gspread

from app.domain.ports import SheetsRepositoryPort

logger = logging.getLogger(__name__)


class SheetsRepository(SheetsRepositoryPort):
    def ensure_schema(self, spreadsheet: gspread.Spreadsheet, schema: dict[str, list[str]]) -> list[str]:
        actions: list[str] = []
        for sheet_name, headers in schema.items():
            worksheet = self._get_or_create(spreadsheet, sheet_name, headers, actions)
            self._ensure_headers(worksheet, headers, actions)
        return actions

    def _get_or_create(
        self,
        spreadsheet: gspread.Spreadsheet,
        sheet_name: str,
        headers: Iterable[str],
        actions: list[str],
    ) -> gspread.Worksheet:
        try:
            return spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            cols = max(10, len(list(headers)) + 2)
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=200, cols=cols)
            actions.append(f"Creada hoja '{sheet_name}'.")
            return worksheet

    def _ensure_headers(
        self, worksheet: gspread.Worksheet, headers: list[str], actions: list[str]
    ) -> None:
        existing = worksheet.row_values(1)
        if not existing:
            worksheet.update("1:1", [headers])
            actions.append(f"Cabecera creada en '{worksheet.title}'.")
            return
        missing = [header for header in headers if header not in existing]
        if missing:
            updated = existing + missing
            worksheet.update("1:1", [updated])
            actions.append(f"Cabecera actualizada en '{worksheet.title}' (añadidas {len(missing)} columnas).")

    def read_personas(self, spreadsheet: gspread.Spreadsheet):
        worksheet = spreadsheet.worksheet("delegadas")
        return self._rows_with_index(worksheet)

    def read_solicitudes(self, spreadsheet: gspread.Spreadsheet):
        worksheet = spreadsheet.worksheet("solicitudes")
        return self._rows_with_index(worksheet)

    def upsert_persona(self, worksheet: gspread.Worksheet, headers: list[str], row: dict[str, object]) -> None:
        self._upsert_row_by_uuid(worksheet, headers, row)

    def upsert_solicitud(self, worksheet: gspread.Worksheet, headers: list[str], row: dict[str, object]) -> None:
        self._upsert_row_by_uuid(worksheet, headers, row)

    def backfill_uuid(self, worksheet: gspread.Worksheet, headers: list[str], row_index: int, uuid_value: str) -> None:
        if "uuid" not in headers:
            headers.append("uuid")
            worksheet.update("1:1", [headers])
        col = headers.index("uuid") + 1
        worksheet.update(gspread.utils.rowcol_to_a1(row_index, col), [[uuid_value]])

    def _rows_with_index(self, worksheet: gspread.Worksheet):
        values = worksheet.get_all_values()
        if not values:
            return [], []
        headers = values[0]
        rows = []
        for row_number, row in enumerate(values[1:], start=2):
            if not any(str(cell).strip() for cell in row):
                continue
            payload = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            payload["__row_number__"] = row_number
            rows.append((row_number, payload))
        return headers, rows

    def _upsert_row_by_uuid(self, worksheet: gspread.Worksheet, headers: list[str], row: dict[str, object]) -> None:
        uuid_value = str(row.get("uuid", "")).strip()
        _, rows = self._rows_with_index(worksheet)
        target = None
        for _, current in rows:
            if str(current.get("uuid", "")).strip() == uuid_value:
                target = int(current.get("__row_number__", 0))
                break
        values = [row.get(header, "") for header in headers]
        if target:
            worksheet.update(f"A{target}:{gspread.utils.rowcol_to_a1(target, len(headers))}", [values])
        else:
            worksheet.append_row(values, value_input_option="USER_ENTERED")
