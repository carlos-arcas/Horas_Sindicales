from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

import gspread

from app.domain.ports import SheetsClientPort
from app.domain.sheets_errors import SheetsRateLimitError
from app.infrastructure.sheets_errors import SheetsApiCompatibilityError, map_gspread_exception

logger = logging.getLogger(__name__)

_MAX_RETRIES = 5
_BASE_BACKOFF_SECONDS = 1
_MAX_JITTER_MS = 300

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
            return spreadsheet
        except Exception as exc:
            raise map_gspread_exception(exc) from exc

    def get_worksheet_values_cached(self, name: str) -> list[list[str]]:
        if name in self._worksheet_values_cache:
            self._avoided_requests_count += 1
            return self._worksheet_values_cache[name]
        worksheet = self.get_worksheet(name)
        values = self._with_rate_limit_retry(
            f"worksheet.get_all_values({name})",
            worksheet.get_all_values,
        )
        self._worksheet_values_cache[name] = values
        self._read_calls_count += 1
        return values

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
        values_by_range = self._with_rate_limit_retry(
            f"spreadsheet.values_batch_get({len(ranges)} ranges)",
            lambda: self._perform_batch_get_ranges(ranges),
        )
        self._read_calls_count += 1
        mapped = self._normalize_batch_get_result(ranges, values_by_range)
        for range_name, normalized_values in mapped.items():
            worksheet_name = self._worksheet_name_from_range(range_name)
            if worksheet_name:
                self._worksheet_values_cache[worksheet_name] = normalized_values
        return mapped

    def _perform_batch_get_ranges(self, ranges: list[str]) -> Any:
        if self._spreadsheet is None:
            raise RuntimeError("Spreadsheet no inicializado. Llama a open_spreadsheet primero.")

        spreadsheet_values_batch_get = getattr(self._spreadsheet, "values_batch_get", None)
        if callable(spreadsheet_values_batch_get):
            return spreadsheet_values_batch_get(ranges)

        if self._client is not None:
            client_values_batch_get = getattr(self._client, "values_batch_get", None)
            if callable(client_values_batch_get):
                return client_values_batch_get(self._spreadsheet.id, ranges)

            http_client = getattr(self._client, "http_client", None)
            if http_client is not None:
                http_values_batch_get = getattr(http_client, "values_batch_get", None)
                if callable(http_values_batch_get):
                    return http_values_batch_get(self._spreadsheet.id, ranges)

        return self._fallback_batch_get_ranges(ranges)

    def _fallback_batch_get_ranges(self, ranges: list[str]) -> dict[str, Any]:
        worksheets = self.get_worksheets_by_title()
        value_ranges: list[dict[str, Any]] = []
        for range_name in ranges:
            worksheet_name = self._worksheet_name_from_range(range_name)
            if not worksheet_name:
                value_ranges.append({"range": range_name, "values": []})
                continue
            worksheet = worksheets.get(worksheet_name)
            if worksheet is None:
                value_ranges.append({"range": range_name, "values": []})
                continue
            local_range = range_name.split("!", 1)[1] if "!" in range_name else range_name
            values = self._with_rate_limit_retry(
                f"worksheet.get({range_name})",
                lambda ws=worksheet, lr=local_range: ws.get(lr),
            )
            normalized_values = values if isinstance(values, list) else []
            value_ranges.append({"range": range_name, "values": normalized_values})
        return {"valueRanges": value_ranges}

    @staticmethod
    def _normalize_batch_get_result(ranges: list[str], values_by_range: Any) -> dict[str, list[list[str]]]:
        mapped: dict[str, list[list[str]]] = {range_name: [] for range_name in ranges}
        if isinstance(values_by_range, dict):
            value_ranges = values_by_range.get("valueRanges", [])
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

    def _with_rate_limit_retry(self, operation_name: str, operation: Callable[[], T]) -> T:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return operation()
            except Exception as exc:
                if isinstance(exc, AttributeError):
                    raise SheetsApiCompatibilityError(
                        "Versión de gspread no soporta batch_get; usa values_batch_get"
                    ) from exc
                mapped_error = map_gspread_exception(exc)
                if not isinstance(mapped_error, SheetsRateLimitError):
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
                jitter_ms = random.randint(0, _MAX_JITTER_MS)
                wait_seconds = backoff_seconds + (jitter_ms / 1000)
                logger.warning(
                    "Rate limit en Google Sheets (%s). intento=%s/%s backoff=%.3fs",
                    operation_name,
                    attempt,
                    _MAX_RETRIES,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
        raise RuntimeError("No se pudo completar la operación de Google Sheets.")

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
