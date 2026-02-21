from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.bootstrap.logging import configure_logging
from app.domain.sheets_errors import SheetsPermissionError
from app.infrastructure.sheets_client import SheetsClient


class _FakeClient:
    def open_by_key(self, _spreadsheet_id: str):
        raise OSError("forbidden")


def test_sheets_permission_error_is_logged_to_error_operativo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    configure_logging(tmp_path)
    monkeypatch.setattr("gspread.service_account", lambda filename: _FakeClient())
    monkeypatch.setattr(
        "app.infrastructure.sheets_client.map_gspread_exception",
        lambda exc: SheetsPermissionError("Permission denied in sheet"),
    )

    client = SheetsClient()
    with pytest.raises(SheetsPermissionError):
        client.open_spreadsheet(Path("cred.json"), "sheet-id")

    operational_log = tmp_path / "error_operativo.log"
    assert operational_log.exists()
    lines = operational_log.read_text(encoding="utf-8").splitlines()
    assert lines
    event = json.loads(lines[-1])
    assert event["mensaje"] == "Sheets permission denied during sync"
    assert "SheetsPermissionError: Permission denied in sheet" in event["exc_info"]
    assert event["extra"]["spreadsheet_id"] == "sheet-id"
