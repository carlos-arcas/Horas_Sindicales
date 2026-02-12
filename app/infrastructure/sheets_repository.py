from __future__ import annotations

import logging
from typing import Iterable

import gspread

from app.domain.ports import SheetsRepositoryPort
from app.infrastructure.sheets_client import execute_with_rate_limit_retry

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
            return execute_with_rate_limit_retry(
                lambda: spreadsheet.worksheet(sheet_name),
                operation_name=f"worksheet({sheet_name})",
            )
        except gspread.WorksheetNotFound:
            cols = max(10, len(list(headers)) + 2)
            worksheet = execute_with_rate_limit_retry(
                lambda: spreadsheet.add_worksheet(title=sheet_name, rows=200, cols=cols),
                operation_name=f"add_worksheet({sheet_name})",
            )
            actions.append(f"Creada hoja '{sheet_name}'.")
            return worksheet

    def _ensure_headers(
        self, worksheet: gspread.Worksheet, headers: list[str], actions: list[str]
    ) -> None:
        existing = execute_with_rate_limit_retry(
            lambda: worksheet.row_values(1),
            operation_name=f"row_values({worksheet.title})",
        )
        if not existing:
            worksheet.update("1:1", [headers])
            actions.append(f"Cabecera creada en '{worksheet.title}'.")
            return
        missing = [header for header in headers if header not in existing]
        if missing:
            updated = existing + missing
            worksheet.update("1:1", [updated])
            actions.append(f"Cabecera actualizada en '{worksheet.title}' (añadidas {len(missing)} columnas).")
