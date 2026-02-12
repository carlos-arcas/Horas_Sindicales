from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import gspread
import pytest

from app.domain.sheets_errors import SheetsRateLimitError
from app.infrastructure.sheets_client import SheetsClient
from app.infrastructure.sheets_errors import map_gspread_exception


class _Resp:
    status_code = 429
    text = "RESOURCE_EXHAUSTED: Quota exceeded for read requests"


def test_map_gspread_exception_429_to_rate_limit() -> None:
    error = gspread.exceptions.APIError(_Resp())
    mapped = map_gspread_exception(error)
    assert isinstance(mapped, SheetsRateLimitError)


def test_open_spreadsheet_retries_rate_limit(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_open_by_key(_spreadsheet_id: str):
        calls["count"] += 1
        if calls["count"] < 3:
            raise gspread.exceptions.APIError(_Resp())
        return SimpleNamespace(id="sheet-id", title="Demo")

    fake_client = SimpleNamespace(open_by_key=fake_open_by_key)
    monkeypatch.setattr("gspread.service_account", lambda filename: fake_client)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    client = SheetsClient()
    spreadsheet = client.open_spreadsheet(Path("/tmp/cred.json"), "sheet-id")

    assert spreadsheet.id == "sheet-id"
    assert calls["count"] == 3


def test_open_spreadsheet_exceeds_retry_limit(monkeypatch) -> None:
    def fake_open_by_key(_spreadsheet_id: str):
        raise gspread.exceptions.APIError(_Resp())

    fake_client = SimpleNamespace(open_by_key=fake_open_by_key)
    monkeypatch.setattr("gspread.service_account", lambda filename: fake_client)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    client = SheetsClient()

    with pytest.raises(SheetsRateLimitError):
        client.open_spreadsheet(Path("/tmp/cred.json"), "sheet-id")
