from __future__ import annotations

import gspread

from app.domain.sheets_errors import SheetsRateLimitError
from app.infrastructure.sheets_errors import map_gspread_exception


class _Response:
    status_code = 429
    text = "[429] Quota exceeded for 'Read requests per minute per user'. RESOURCE_EXHAUSTED RATE_LIMIT_EXCEEDED"


def test_map_gspread_exception_maps_429_to_rate_limit() -> None:
    api_error = gspread.exceptions.APIError(_Response())

    mapped = map_gspread_exception(api_error)

    assert isinstance(mapped, SheetsRateLimitError)
    assert "Límite de Google Sheets" in str(mapped)
