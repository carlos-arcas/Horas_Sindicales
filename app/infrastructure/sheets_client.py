from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

import gspread
from google.auth.exceptions import DefaultCredentialsError

from app.core.observability import get_correlation_id
from app.core.operational_logging import log_operational_error
from app.domain.ports import SheetsClientPort
from app.domain.sheets_errors import SheetsPermissionError, SheetsRateLimitError
from app.infrastructure.sheets_errors import SheetsApiCompatibilityError, map_gspread_exception

logger = logging.getLogger(__name__)

_MAX_RETRIES = 5
_BASE_BACKOFF_SECONDS = 1
_WRITE_MAX_RETRIES = 5

T = TypeVar("T")


class SheetsClient(SheetsClientPort):
    def __init__(self) -> None:
        self._client: Any | None = None
        self._spreadsheet: gspread.Spreadsheet | None = None
        self._worksheet_values_cache: dict[str, list[list[str]]] = {}
        self._worksheet_cache: dict[str, gspread.Worksheet] = {}
        self._worksheets_by_title_cache: dict[str, gspread.Worksheet] | None = None
        self._read_calls_count = 0
        self._avoided_requests_count = 0
        self._write_calls_count = 0

    def open_spreadsheet(self, credentials_path: Path, spreadsheet_id: str) -> gspread.Spreadsheet:
        logger.info("Conectando a Google Sheets con credenciales: %s", credentials_path)
        try:
            client = gspread.service_account(filename=str(credentials_path))
            self._client = client
            spreadsheet = self._with_rate_limit_retry(
                "open_spreadsheet",
                lambda: client.open_by_key(spreadsheet_id),
            )
            self._spreadsheet = spreadsheet
            self._worksheet_values_cache = {}
            self._worksheet_cache = {}
            self._worksheets_by_title_cache = None
            self._read_calls_count = 0
            self._avoided_requests_count = 0
            self._write_calls_count = 0
            return spreadsheet
        except (
            gspread.exceptions.GSpreadException,
            FileNotFoundError,
            json.JSONDecodeError,
            DefaultCredentialsError,
            AttributeError,
            OSError,
        ) as exc:
            mapped_error = map_gspread_exception(exc)
            if isinstance(mapped_error, SheetsPermissionError):
                self._log_permission_error(
                    mapped_error,
                    spreadsheet_id=spreadsheet_id,
                )
            raise mapped_error from exc

    def read_all_values(self, worksheet_name: str) -> list[list[str]]:
        if worksheet_name in self._worksheet_values_cache:
            self._avoided_requests_count += 1
            return self._worksheet_values_cache[worksheet_name]
        worksheet = self.get_worksheet(worksheet_name)
        values = self._with_rate_limit_retry(
            f"worksheet.get_all_values({worksheet_name})",
            worksheet.get_all_values,
        )
        self._worksheet_values_cache[worksheet_name] = values
        self._read_calls_count += 1
        return values

    # Backward-compatible alias for existing collaborators/tests.
    def get_worksheet_values_cached(self, name: str) -> list[list[str]]:
        return self.read_all_values(name)

    def get_worksheet(self, name: str):
        if name in self._worksheet_cache:
            self._avoided_requests_count += 1
            return self._worksheet_cache[name]
        if self._spreadsheet is None:
            raise RuntimeError("Spreadsheet no inicializado. Llama a open_spreadsheet primero.")
        worksheet = self._with_rate_limit_retry(
            f"spreadsheet.worksheet({name})",
            lambda: self._spreadsheet.worksheet(name),
        )
        self._worksheet_cache[name] = worksheet
        return worksheet

    def get_worksheets_by_title(self) -> dict[str, gspread.Worksheet]:
        if self._worksheets_by_title_cache is not None:
            self._avoided_requests_count += 1
            return self._worksheets_by_title_cache
        if self._spreadsheet is None:
            raise RuntimeError("Spreadsheet no inicializado. Llama a open_spreadsheet primero.")
        worksheets = self._with_rate_limit_retry("spreadsheet.worksheets", self._spreadsheet.worksheets)
        self._worksheets_by_title_cache = {worksheet.title: worksheet for worksheet in worksheets}
        self._worksheet_cache.update(self._worksheets_by_title_cache)
        self._read_calls_count += 1
        return self._worksheets_by_title_cache

    def batch_get_ranges(self, ranges: list[str]) -> dict[str, list[list[str]]]:
        if self._spreadsheet is None:
            raise RuntimeError("Spreadsheet no inicializado. Llama a open_spreadsheet primero.")
        if not ranges:
            return {}
        logger.debug("values_batch_get %s ranges", len(ranges))
        values_by_range = self._with_rate_limit_retry(
            f"spreadsheet.values_batch_get({len(ranges)} ranges)",
            lambda: self._spreadsheet.values_batch_get(ranges),
        )
        self._read_calls_count += 1
        mapped = self._normalize_batch_get_result(ranges, values_by_range)
        for range_name, normalized_values in mapped.items():
            worksheet_name = self._worksheet_name_from_range(range_name)
            if worksheet_name:
                self._worksheet_values_cache[worksheet_name] = normalized_values
        return mapped

    @staticmethod
    def _normalize_batch_get_result(ranges: list[str], values_by_range: Any) -> dict[str, list[list[str]]]:
        mapped: dict[str, list[list[str]]] = {range_name: [] for range_name in ranges}
        if isinstance(values_by_range, dict):
            value_ranges = values_by_range.get("valueRanges", [])
            logger.debug("values_batch_get returned %s valueRanges", len(value_ranges) if isinstance(value_ranges, list) else 0)
            if isinstance(value_ranges, list):
                for value_range in value_ranges:
                    if not isinstance(value_range, dict):
                        continue
                    range_name = value_range.get("range")
                    if not isinstance(range_name, str):
                        continue
                    values = value_range.get("values", [])
                    mapped[range_name] = values if isinstance(values, list) else []
            return mapped
        if isinstance(values_by_range, list):
            for range_name, values in zip(ranges, values_by_range):
                mapped[range_name] = values if isinstance(values, list) else []
            return mapped
        raise SheetsApiCompatibilityError("Versión de gspread no soporta batch_get; usa values_batch_get")

    def get_read_calls_count(self) -> int:
        return self._read_calls_count

    def get_avoided_requests_count(self) -> int:
        return self._avoided_requests_count

    def get_write_calls_count(self) -> int:
        return self._write_calls_count

    def append_rows(self, worksheet_name: str, rows: list[list[Any]]) -> None:
        if not rows:
            return
        worksheet = self.get_worksheet(worksheet_name)
        self._with_write_retry(
            f"worksheet.append_rows({worksheet_name})",
            lambda: worksheet.append_rows(rows, value_input_option="USER_ENTERED"),
        )
        self._write_calls_count += 1

    def batch_update(self, worksheet_name: str, data: list[dict[str, Any]]) -> None:
        if not data:
            return
        worksheet = self.get_worksheet(worksheet_name)
        self._with_write_retry(
            f"worksheet.batch_update({worksheet_name})",
            lambda: worksheet.batch_update(data, value_input_option="USER_ENTERED"),
        )
        self._write_calls_count += 1

    def values_batch_update(self, body: dict[str, Any]) -> None:
        if not body.get("data"):
            return
        if self._spreadsheet is None:
            raise RuntimeError("Spreadsheet no inicializado. Llama a open_spreadsheet primero.")
        self._with_write_retry(
            "spreadsheet.values_batch_update",
            lambda: self._spreadsheet.values_batch_update(body),
        )
        self._write_calls_count += 1

    def _with_rate_limit_retry(self, operation_name: str, operation: Callable[[], T]) -> T:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return operation()
            except gspread.exceptions.APIError as exc:
                mapped_error = map_gspread_exception(exc)
                if not isinstance(mapped_error, SheetsRateLimitError):
                    if isinstance(mapped_error, SheetsPermissionError):
                        self._log_permission_error(
                            mapped_error,
                            spreadsheet_id=getattr(self._spreadsheet, "id", None),
                            worksheet_name=self._worksheet_from_operation_name(operation_name),
                        )
                    raise mapped_error from exc
                if attempt >= _MAX_RETRIES:
                    logger.error(
                        "Google Sheets rate limit persistente en %s tras %s intentos.",
                        operation_name,
                        attempt,
                    )
                    raise SheetsRateLimitError(
                        "Límite de Google Sheets alcanzado. Espera 1 minuto y reintenta."
                    ) from exc
                backoff_seconds = _BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Rate limit en Google Sheets (%s). intento=%s/%s backoff=%.3fs",
                    operation_name,
                    attempt,
                    _MAX_RETRIES,
                    backoff_seconds,
                )
                time.sleep(backoff_seconds)
        raise RuntimeError("No se pudo completar la operación de Google Sheets.")

    def _with_write_retry(self, operation_name: str, operation: Callable[[], T]) -> T:
        for attempt in range(1, _WRITE_MAX_RETRIES + 1):
            try:
                return operation()
            except gspread.exceptions.APIError as exc:
                mapped_error = map_gspread_exception(exc)
                if not isinstance(mapped_error, SheetsRateLimitError):
                    if isinstance(mapped_error, SheetsPermissionError):
                        self._log_permission_error(
                            mapped_error,
                            spreadsheet_id=getattr(self._spreadsheet, "id", None),
                            worksheet_name=self._worksheet_from_operation_name(operation_name),
                        )
                    raise mapped_error from exc
                if attempt >= _WRITE_MAX_RETRIES:
                    logger.error(
                        "Google Sheets rate limit persistente en escritura %s tras %s intentos.",
                        operation_name,
                        attempt,
                    )
                    raise SheetsRateLimitError(
                        "Límite de escritura de Google Sheets alcanzado. Espera 1 minuto y reintenta."
                    ) from exc
                backoff_seconds = 2 ** (attempt - 1)
                logger.warning(
                    "Rate limit en escritura Google Sheets (%s). intento=%s/%s backoff=%ss",
                    operation_name,
                    attempt,
                    _WRITE_MAX_RETRIES,
                    backoff_seconds,
                )
                time.sleep(backoff_seconds)
        raise RuntimeError("No se pudo completar la escritura en Google Sheets.")

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

    @staticmethod
    def _worksheet_from_operation_name(operation_name: str) -> str | None:
        start = operation_name.find("(")
        end = operation_name.rfind(")")
        if start < 0 or end <= start:
            return None
        worksheet_name = operation_name[start + 1 : end].strip()
        return worksheet_name or None

    @staticmethod
    def _log_permission_error(
        error: SheetsPermissionError,
        *,
        spreadsheet_id: str | None = None,
        worksheet_name: str | None = None,
    ) -> None:
        log_operational_error(
            "Sheets permission denied during sync",
            exc=error,
            extra={
                "operation": "sheets_access",
                "correlation_id": get_correlation_id(),
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet_name,
            },
        )
