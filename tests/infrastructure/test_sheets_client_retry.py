from __future__ import annotations

from types import SimpleNamespace

import gspread
import pytest

from app.domain.sheets_errors import SheetsPermissionError
from app.infrastructure.sheets_client import SheetsClient


class _ForbiddenResp:
    status_code = 403
    text = '{"error": {"code": 403, "message": "The caller does not have permission", "status": "PERMISSION_DENIED"}}'


def test_with_write_retry_returns_operation_result() -> None:
    client = SheetsClient()

    result = client._with_write_retry("worksheet.append_rows(MiHoja)", lambda: "ok")

    assert result == "ok"


def test_with_write_retry_permission_error_never_raises_name_error(monkeypatch) -> None:
    client = SheetsClient()

    def fail_operation():
        raise gspread.exceptions.APIError(_ForbiddenResp())

    captured = {}

    def fake_log_permission_error(error: SheetsPermissionError, *, spreadsheet_id: str | None = None, worksheet_name: str | None = None) -> None:
        captured["error"] = error
        captured["spreadsheet_id"] = spreadsheet_id
        captured["worksheet_name"] = worksheet_name

    monkeypatch.setattr(client, "_log_permission_error", fake_log_permission_error)

    with pytest.raises(SheetsPermissionError):
        client._with_write_retry("worksheet.append_rows(Asistencia)", fail_operation)

    assert isinstance(captured["error"], SheetsPermissionError)
    assert captured["worksheet_name"] == "Asistencia"


def test_with_write_retry_preserves_context_with_inferred_spreadsheet_id(monkeypatch) -> None:
    client = SheetsClient()
    client._spreadsheet = SimpleNamespace(id="spreadsheet-123")

    def fail_operation():
        raise gspread.exceptions.APIError(_ForbiddenResp())

    captured: dict[str, str | None] = {}

    def fake_log_permission_error(_error: SheetsPermissionError, *, spreadsheet_id: str | None = None, worksheet_name: str | None = None) -> None:
        captured["spreadsheet_id"] = spreadsheet_id
        captured["worksheet_name"] = worksheet_name

    monkeypatch.setattr(client, "_log_permission_error", fake_log_permission_error)

    with pytest.raises(SheetsPermissionError):
        client._with_write_retry("worksheet.batch_update(Resumen)", fail_operation)

    assert captured["spreadsheet_id"] == "spreadsheet-123"
    assert captured["worksheet_name"] == "Resumen"


def test_with_write_retry_context_handles_missing_spreadsheet_id(monkeypatch) -> None:
    client = SheetsClient()

    def fail_operation():
        raise gspread.exceptions.APIError(_ForbiddenResp())

    captured: dict[str, str | None] = {}

    def fake_log_permission_error(_error: SheetsPermissionError, *, spreadsheet_id: str | None = None, worksheet_name: str | None = None) -> None:
        captured["spreadsheet_id"] = spreadsheet_id
        captured["worksheet_name"] = worksheet_name

    monkeypatch.setattr(client, "_log_permission_error", fake_log_permission_error)

    with pytest.raises(SheetsPermissionError):
        client._with_write_retry("worksheet.append_rows(SinID)", fail_operation)

    assert captured["spreadsheet_id"] is None
    assert captured["worksheet_name"] == "SinID"


def test_with_write_retry_usa_spreadsheet_id_explicito(monkeypatch) -> None:
    client = SheetsClient()

    def fail_operation():
        raise gspread.exceptions.APIError(_ForbiddenResp())

    captured: dict[str, str | None] = {}

    def fake_log_permission_error(_error: SheetsPermissionError, *, spreadsheet_id: str | None = None, worksheet_name: str | None = None) -> None:
        captured["spreadsheet_id"] = spreadsheet_id
        captured["worksheet_name"] = worksheet_name

    monkeypatch.setattr(client, "_log_permission_error", fake_log_permission_error)

    with pytest.raises(SheetsPermissionError):
        client._with_write_retry("worksheet.append_rows(Explícito)", fail_operation, spreadsheet_id="sheet-explicit")

    assert captured["spreadsheet_id"] == "sheet-explicit"
    assert captured["worksheet_name"] == "Explícito"


def test_with_write_retry_non_api_exception_is_reraised() -> None:
    client = SheetsClient()

    def fail_operation():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        client._with_write_retry("worksheet.append_rows(Hoja)", fail_operation)
