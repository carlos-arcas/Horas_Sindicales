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
            self._worksheet_values_cache.clear()
            return self._spreadsheet
        except Exception as exc:
            raise map_gspread_exception(exc) from exc

    def get_worksheet_values_cached(self, name: str) -> list[list[str]]:
        if name in self._worksheet_values_cache:
            return self._worksheet_values_cache[name]
        spreadsheet = self._require_spreadsheet()
        worksheet = spreadsheet.worksheet(name)
        values = worksheet.get_all_values()
        self._worksheet_values_cache[name] = values
        self._read_calls_count += 1
        return values

    def batch_get_ranges(self, ranges: list[str]) -> dict[str, list[list[str]]]:
        if not ranges:
            return {}
        spreadsheet = self._require_spreadsheet()
        response = spreadsheet.batch_get(ranges)
        self._read_calls_count += 1
        result: dict[str, list[list[str]]] = {}
        for requested_range, values in zip(ranges, response, strict=False):
            worksheet_name = self._worksheet_name_from_range(requested_range)
            normalized_values = values if values else []
            result[worksheet_name] = normalized_values
            self._worksheet_values_cache[worksheet_name] = normalized_values
        return result

    def reset_read_calls_count(self) -> None:
        self._read_calls_count = 0

    def get_read_calls_count(self) -> int:
        return self._read_calls_count

    def _require_spreadsheet(self) -> gspread.Spreadsheet:
        if self._spreadsheet is None:
            raise RuntimeError("No hay hoja de cálculo abierta. Ejecuta open_spreadsheet primero.")
        return self._spreadsheet

    @staticmethod
    def _worksheet_name_from_range(range_name: str) -> str:
        worksheet_name = range_name.split("!", maxsplit=1)[0].strip()
        if worksheet_name.startswith("'") and worksheet_name.endswith("'"):
            return worksheet_name[1:-1]
        return worksheet_name
