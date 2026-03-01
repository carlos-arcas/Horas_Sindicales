from __future__ import annotations

from dataclasses import dataclass

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.domain.models import SheetsConfig
from app.domain.sheets_errors import SheetsPermissionError


@dataclass
class _FakeConfigStore:
    config: SheetsConfig

    def load(self) -> SheetsConfig:
        return self.config


class _FakeClientPermissionDenied:
    def __init__(self) -> None:
        self.append_rows_calls = 0

    def open_spreadsheet(self, *_args):
        class _Spreadsheet:
            id = "sheet-123"

        return _Spreadsheet()

    def get_worksheets_by_title(self):
        return {
            "delegadas": object(),
            "solicitudes": object(),
            "pdf_log": object(),
            "sync_config": object(),
        }

    def check_write_access(self, worksheet_name: str | None = None) -> None:
        raise SheetsPermissionError("403 Forbidden", worksheet=worksheet_name)

    def append_rows(self, worksheet_name: str, rows):
        self.append_rows_calls += 1

    def get_write_calls_count(self) -> int:
        return 0

    def get_read_calls_count(self) -> int:
        return 0

    def get_avoided_requests_count(self) -> int:
        return 0

    def get_sheets_api_calls_count(self) -> int:
        return 0


class _FakeRepository:
    def ensure_schema(self, *_args, **_kwargs):
        return []


def _build_service(connection) -> tuple[SheetsSyncService, _FakeClientPermissionDenied]:
    client = _FakeClientPermissionDenied()
    config = SheetsConfig("sheet-123", "/tmp/creds.json", "device-1")
    service = SheetsSyncService(
        connection=connection,
        config_store=_FakeConfigStore(config),
        client=client,
        repository=_FakeRepository(),
    )
    return service, client


def test_preflight_permissions_denied_blocks_push_without_writes(connection, monkeypatch) -> None:
    monkeypatch.setenv("SYNC_STRICT_EXCEPTIONS", "false")
    service, client = _build_service(connection)

    preflight = service.preflight_permisos_escritura(service._ensure_connection_ready())

    assert preflight.ok is False
    assert preflight.issues[0].tipo == "PERMISSION_DENIED"

    summary = service.push()

    assert summary.errors == 1
    assert client.append_rows_calls == 0
