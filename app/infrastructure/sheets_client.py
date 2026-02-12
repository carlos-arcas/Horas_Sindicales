from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import Callable, TypeVar

import gspread

from app.domain.ports import SheetsClientPort
from app.domain.sheets_errors import SheetsRateLimitError
from app.infrastructure.sheets_errors import map_gspread_exception

logger = logging.getLogger(__name__)

T = TypeVar("T")
_MAX_RETRIES = 5
_BASE_BACKOFF_SECONDS = 1
_MAX_JITTER_SECONDS = 0.3


def execute_with_rate_limit_retry(operation: Callable[[], T], *, operation_name: str) -> T:
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return operation()
        except Exception as exc:
            mapped = map_gspread_exception(exc)
            if not isinstance(mapped, SheetsRateLimitError):
                raise mapped from exc
            if attempt == _MAX_RETRIES:
                logger.error(
                    "Google Sheets rate limit persistente en %s tras %s intentos.",
                    operation_name,
                    _MAX_RETRIES,
                )
                raise SheetsRateLimitError(
                    "Límite de Google Sheets alcanzado. Espera 1 minuto y reintenta."
                ) from exc
            backoff = _BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            jitter = random.uniform(0, _MAX_JITTER_SECONDS)
            sleep_time = backoff + jitter
            logger.warning(
                "Rate limit en %s (intento %s/%s). Backoff %.3fs (base=%ss, jitter=%.3fs).",
                operation_name,
                attempt,
                _MAX_RETRIES,
                sleep_time,
                backoff,
                jitter,
            )
            time.sleep(sleep_time)
    raise SheetsRateLimitError("Límite de Google Sheets alcanzado. Espera 1 minuto y reintenta.")


class SheetsClient(SheetsClientPort):
    def open_spreadsheet(self, credentials_path: Path, spreadsheet_id: str) -> gspread.Spreadsheet:
        logger.info("Conectando a Google Sheets con credenciales: %s", credentials_path)

        def _open() -> gspread.Spreadsheet:
            client = gspread.service_account(filename=str(credentials_path))
            return client.open_by_key(spreadsheet_id)

        return execute_with_rate_limit_retry(_open, operation_name="open_spreadsheet")
