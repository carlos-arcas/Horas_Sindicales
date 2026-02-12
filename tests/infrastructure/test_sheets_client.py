from __future__ import annotations

import gspread

from app.domain.sheets_errors import SheetsRateLimitError
from app.infrastructure.sheets_client import SheetsClient


class _FakeResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def _rate_limit_error() -> gspread.exceptions.APIError:
    return gspread.exceptions.APIError(
        _FakeResponse(429, "RESOURCE_EXHAUSTED: Quota exceeded for read requests per minute")
    )


class _FakeGspreadClient:
    def __init__(self, fail_times: int = 0) -> None:
        self._fail_times = fail_times
        self.calls = 0

    def open_by_key(self, _: str):
        self.calls += 1
        if self.calls <= self._fail_times:
            raise _rate_limit_error()
        return "ok"


def test_open_spreadsheet_retry_hasta_exito(monkeypatch) -> None:
    fake_client = _FakeGspreadClient(fail_times=2)
    sleep_calls: list[float] = []

    monkeypatch.setattr("app.infrastructure.sheets_client.gspread.service_account", lambda filename: fake_client)
    monkeypatch.setattr("app.infrastructure.sheets_client.time.sleep", sleep_calls.append)
    monkeypatch.setattr("app.infrastructure.sheets_client.random.randint", lambda a, b: 0)

    result = SheetsClient().open_spreadsheet("/tmp/credentials.json", "sheet-id")

    assert result == "ok"
    assert fake_client.calls == 3
    assert sleep_calls == [1, 2]


def test_open_spreadsheet_lanza_rate_limit_al_agotar_reintentos(monkeypatch) -> None:
    fake_client = _FakeGspreadClient(fail_times=5)

    monkeypatch.setattr("app.infrastructure.sheets_client.gspread.service_account", lambda filename: fake_client)
    monkeypatch.setattr("app.infrastructure.sheets_client.time.sleep", lambda _: None)
    monkeypatch.setattr("app.infrastructure.sheets_client.random.randint", lambda a, b: 0)

    try:
        SheetsClient().open_spreadsheet("/tmp/credentials.json", "sheet-id")
        assert False, "Expected SheetsRateLimitError"
    except SheetsRateLimitError:
        pass
