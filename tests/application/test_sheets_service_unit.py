from __future__ import annotations

from pathlib import Path

import pytest

from app.application.sheets_service import SHEETS_SCHEMA, SheetsService
from app.domain.models import SheetsConfig
from app.domain.services import BusinessRuleError
from app.domain.sheets_errors import SheetsCredentialsError


class FakeConfigRepo:
    def __init__(self, current: SheetsConfig | None = None, credentials_path: Path | None = None) -> None:
        self._current = current
        self._saved: list[SheetsConfig] = []
        self._credentials_path = credentials_path or Path("/tmp/credentials.json")

    def load(self) -> SheetsConfig | None:
        return self._current

    def save(self, config: SheetsConfig) -> SheetsConfig:
        self._saved.append(config)
        self._current = config
        return config

    def credentials_path(self) -> Path:
        return self._credentials_path


class FakeGateway:
    def __init__(self, result: tuple[str, str, list[str]] | None = None) -> None:
        self.result = result or ("Libro", "abc123", ["created:delegadas"])
        self.calls: list[tuple[SheetsConfig, dict[str, list[str]]]] = []

    def test_connection(self, config: SheetsConfig, schema: dict[str, list[str]]) -> tuple[str, str, list[str]]:
        self.calls.append((config, schema))
        return self.result


def test_normalize_spreadsheet_id_from_url_or_plain_id() -> None:
    assert SheetsService._normalize_spreadsheet_id("https://docs.google.com/spreadsheets/d/ABC-123_xyz/edit") == "ABC-123_xyz"
    assert SheetsService._normalize_spreadsheet_id(" raw-id ") == "raw-id"


def test_save_config_uses_existing_credentials_and_device_id() -> None:
    existing = SheetsConfig(spreadsheet_id="old", credentials_path="/creds.json", device_id="dev-1")
    service = SheetsService(config_repo=FakeConfigRepo(current=existing), gateway=FakeGateway())

    saved = service.save_config("https://docs.google.com/spreadsheets/d/new-sheet-id/edit")

    assert saved.spreadsheet_id == "new-sheet-id"
    assert saved.credentials_path == "/creds.json"
    assert saved.device_id == "dev-1"


def test_save_config_raises_business_error_when_credentials_missing() -> None:
    service = SheetsService(config_repo=FakeConfigRepo(current=None), gateway=FakeGateway())

    with pytest.raises(BusinessRuleError):
        service.save_config("sheet-id", credentials_path="")


def test_test_connection_calls_gateway_with_schema_and_returns_result(tmp_path: Path) -> None:
    credentials = tmp_path / "credentials.json"
    credentials.write_text("{}", encoding="utf-8")

    gateway = FakeGateway(result=("Planilla principal", "sheet-999", ["ok"]))
    service = SheetsService(config_repo=FakeConfigRepo(), gateway=gateway)

    result = service.test_connection("sheet-999", credentials_path=str(credentials))

    assert result.spreadsheet_title == "Planilla principal"
    assert result.spreadsheet_id == "sheet-999"
    assert result.schema_actions == ["ok"]
    assert gateway.calls and gateway.calls[0][1] == SHEETS_SCHEMA


def test_validate_credentials_file_rejects_empty_or_missing_file(tmp_path: Path) -> None:
    with pytest.raises(BusinessRuleError):
        SheetsService._validate_credentials_file("")

    missing = tmp_path / "missing.json"
    with pytest.raises(SheetsCredentialsError):
        SheetsService._validate_credentials_file(str(missing))
