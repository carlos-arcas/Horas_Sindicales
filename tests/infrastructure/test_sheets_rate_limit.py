from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import gspread
import pytest

from app.domain.sheets_errors import SheetsPermissionError, SheetsRateLimitError
from app.infrastructure.sheets_client import SheetsClient
from app.infrastructure.sheets_errors import map_gspread_exception


class _Resp:
    status_code = 429
    text = "RESOURCE_EXHAUSTED: Quota exceeded for read requests"


class _ForbiddenResp:
    status_code = 403
    text = '{"error": {"code": 403, "message": "The caller does not have permission", "status": "PERMISSION_DENIED"}}'


def test_map_gspread_exception_429_to_rate_limit() -> None:
    error = gspread.exceptions.APIError(_Resp())
    mapped = map_gspread_exception(error)
    assert isinstance(mapped, SheetsRateLimitError)


def test_map_gspread_exception_403_to_permission_error() -> None:
    error = gspread.exceptions.APIError(_ForbiddenResp())
    mapped = map_gspread_exception(error)
    assert isinstance(mapped, SheetsPermissionError)


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


def test_batch_get_ranges_normalizes_value_ranges() -> None:
    client = SheetsClient()
    normalized = client._normalize_batch_get_result(
        ["A!A1:B2", "B!A1:A2"],
        {
            "valueRanges": [
                {"range": "A!A1:B2", "values": [["1", "2"], ["3", "4"]]},
                {"range": "B!A1:A2", "values": [["x"], ["y"]]},
            ]
        },
    )
    assert normalized == {
        "A!A1:B2": [["1", "2"], ["3", "4"]],
        "B!A1:A2": [["x"], ["y"]],
    }


def test_with_rate_limit_retry_does_not_retry_attribute_error() -> None:
    client = SheetsClient()
    calls = {"count": 0}

    def operation():
        calls["count"] += 1
        raise AttributeError("missing")

    with pytest.raises(AttributeError) as err:
        client._with_rate_limit_retry("attr", operation)

    assert "missing" in str(err.value)
    assert calls["count"] == 1
