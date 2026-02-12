from __future__ import annotations

import gspread

from app.domain.sheets_errors import SheetsRateLimitError
from app.infrastructure.sheets_errors import is_rate_limited_api_error, map_gspread_exception


class _FakeResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def _api_error(status_code: int, text: str) -> gspread.exceptions.APIError:
    return gspread.exceptions.APIError(_FakeResponse(status_code, text))


def test_map_gspread_exception_maps_429_to_rate_limit_error() -> None:
    ex = _api_error(429, "RESOURCE_EXHAUSTED: Quota exceeded for read requests")

    mapped = map_gspread_exception(ex)

    assert isinstance(mapped, SheetsRateLimitError)


def test_is_rate_limited_api_error_detects_rate_limit_markers() -> None:
    ex = _api_error(400, "RATE_LIMIT_EXCEEDED")

    assert is_rate_limited_api_error(ex) is True
