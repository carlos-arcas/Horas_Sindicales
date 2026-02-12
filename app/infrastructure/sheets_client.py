from __future__ import annotations

import logging
from pathlib import Path

import gspread

from app.domain.ports import SheetsClientPort
from app.infrastructure.sheets_errors import map_gspread_exception

logger = logging.getLogger(__name__)


class SheetsClient(SheetsClientPort):
    def __init__(self) -> None:
        self._spreadsheet: gspread.Spreadsheet | None = None
        self._worksheet_values_cache: dict[str, list[list[str]]] = {}
        self._read_calls_count = 0

    def open_spreadsheet(self, credentials_path: Path, spreadsheet_id: str) -> gspread.Spreadsheet:
        logger.info("Conectando a Google Sheets con credenciales: %s", credentials_path)
        try:
            client = gspread.service_account(filename=str(credentials_path))
            self._spreadsheet = client.open_by_key(spreadsheet_id)
            self._worksheet_values_cache = {}
            self._read_calls_count = 0
            return self._spreadsheet
        except Exception as exc:
            raise map_gspread_exception(exc) from exc

    def get_worksheet_values_cached(self, name: str) -> list[list[str]]:
        if name in self._worksheet_values_cache:
            return self._worksheet_values_cache[name]
        if self._spreadsheet is None:
            raise RuntimeError("Spreadsheet no inicializado. Llama a open_spreadsheet primero.")
        worksheet = self._spreadsheet.worksheet(name)
        values = worksheet.get_all_values()
        self._worksheet_values_cache[name] = values
        self._read_calls_count += 1
        return values

    def batch_get_ranges(self, ranges: list[str]) -> dict[str, list[list[str]]]:
        if self._spreadsheet is None:
            raise RuntimeError("Spreadsheet no inicializado. Llama a open_spreadsheet primero.")
        if not ranges:
            return {}
        values_by_range = self._spreadsheet.batch_get(ranges)
        self._read_calls_count += 1
        mapped: dict[str, list[list[str]]] = {}
        for range_name, values in zip(ranges, values_by_range):
            normalized_values = values if isinstance(values, list) else []
            mapped[range_name] = normalized_values
            worksheet_name = self._worksheet_name_from_range(range_name)
            if worksheet_name:
                self._worksheet_values_cache[worksheet_name] = normalized_values
        return mapped

    def get_read_calls_count(self) -> int:
        return self._read_calls_count

    @staticmethod
    def _worksheet_name_from_range(range_name: str) -> str | None:
        if "!" in range_name:
            sheet_part = range_name.split("!", 1)[0].strip()
        else:
            sheet_part = range_name.strip()
        if not sheet_part:
            return None
        if sheet_part.startswith("'") and sheet_part.endswith("'"):
            sheet_part = sheet_part[1:-1].replace("''", "'")
        return sheet_part
