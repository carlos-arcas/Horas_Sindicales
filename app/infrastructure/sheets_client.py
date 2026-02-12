from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import Callable, TypeVar

import gspread

from app.domain.ports import SheetsClientPort
from app.domain.sheets_errors import SheetsRateLimitError
from app.infrastructure.sheets_errors import is_rate_limited_api_error, map_gspread_exception

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SheetsClient(SheetsClientPort):
    _MAX_ATTEMPTS = 5
    _BACKOFF_SECONDS = (1, 2, 4, 8, 16)

    def open_spreadsheet(self, credentials_path: Path, spreadsheet_id: str) -> gspread.Spreadsheet:
        logger.info("Conectando a Google Sheets con credenciales: %s", credentials_path)
        try:
            client = gspread.service_account(filename=str(credentials_path))
        except Exception as exc:
            raise map_gspread_exception(exc) from exc
        return self._retry_rate_limited(
            lambda: client.open_by_key(spreadsheet_id),
            operation=f"open_by_key({spreadsheet_id})",
        )

    def _retry_rate_limited(self, action: Callable[[], T], operation: str) -> T:
        last_exc: Exception | None = None
        for attempt in range(1, self._MAX_ATTEMPTS + 1):
            try:
                return action()
            except Exception as exc:
                if not is_rate_limited_api_error(exc):
                    raise map_gspread_exception(exc) from exc
                last_exc = exc
                if attempt >= self._MAX_ATTEMPTS:
                    break
                backoff = self._BACKOFF_SECONDS[attempt - 1]
                jitter_ms = random.randint(0, 300)
                sleep_seconds = backoff + (jitter_ms / 1000)
                logger.warning(
                    "Google Sheets rate limit en %s (intento %s/%s). Reintentando en %.3fs",
                    operation,
                    attempt,
                    self._MAX_ATTEMPTS,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
        logger.error(
            "Google Sheets rate limit persistente en %s tras %s intentos",
            operation,
            self._MAX_ATTEMPTS,
        )
        raise SheetsRateLimitError(
            "Límite de Google Sheets alcanzado. Espera 1 minuto y reintenta."
        ) from last_exc
