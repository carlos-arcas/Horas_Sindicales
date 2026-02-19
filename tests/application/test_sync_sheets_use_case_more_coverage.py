from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

import pytest

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.core.errors import InfraError
from app.domain.models import SheetsConfig
from app.domain.sheets_errors import SheetsConfigError, SheetsRateLimitError


@dataclass
class _FakeConfigStore:
    config: SheetsConfig | None

    def load(self) -> SheetsConfig | None:
        return self.config


class _FakeClient:
    def __init__(self) -> None:
        self.get_worksheet = Mock(return_value={"title": "solicitudes"})
        self.open_spreadsheet = Mock(return_value=object())
        self.get_worksheets_by_title = Mock(return_value={})


class _FakeRepository:
    def ensure_schema(self, *_: Any, **__: Any) -> list[str]:
        return []


def _build_service(connection, *, config: SheetsConfig | None = None, client: _FakeClient | None = None) -> SheetsSyncService:
    effective_client = client or _FakeClient()
    effective_config = config or SheetsConfig("sheet-id", "/tmp/creds.json", "device-local")
    return SheetsSyncService(
        connection=connection,
        config_store=_FakeConfigStore(effective_config),
        client=effective_client,
        repository=_FakeRepository(),
    )


def test_store_sync_config_value_not_configured_skips_write(connection) -> None:
    service = _build_service(connection, config=SheetsConfig("", "", "device-local"))

    service.store_sync_config_value("mode", "manual")

    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM sync_config")
    assert cursor.fetchone()["total"] == 0


def test_register_pdf_log_returns_early_without_hash_and_unknown_persona(connection, persona_id) -> None:
    service = _build_service(connection)

    service.register_pdf_log(persona_id, ["2025-01-01"], None)
    service.register_pdf_log(999_999, ["2025-01-01"], "hash-pdf-1")

    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM pdf_log")
    assert cursor.fetchone()["total"] == 0


def test_prepare_sync_context_reraises_rate_limit(connection) -> None:
    client = _FakeClient()
    client.get_worksheets_by_title.side_effect = SheetsRateLimitError("rate limited")
    service = _build_service(connection, client=client)

    with pytest.raises(SheetsRateLimitError):
        service._prepare_sync_context(object())


def test_prepare_sync_context_falls_back_to_on_demand_fetch_on_infra_error(connection) -> None:
    client = _FakeClient()
    client.get_worksheets_by_title.side_effect = InfraError("cache metadata unavailable")
    worksheet = {"title": "solicitudes"}
    client.get_worksheet.return_value = worksheet
    service = _build_service(connection, client=client)

    service._prepare_sync_context(object())

    loaded = service._get_worksheet(object(), "solicitudes")
    cached = service._get_worksheet(object(), "solicitudes")
    assert loaded == worksheet
    assert cached == worksheet
    assert client.get_worksheet.call_count == 1


def test_solicitudes_pull_source_titles_raises_when_no_supported_sheets(connection) -> None:
    client = _FakeClient()
    client.get_worksheets_by_title.return_value = {"otra_hoja": object()}
    service = _build_service(connection, client=client)

    with pytest.raises(SheetsConfigError):
        service._solicitudes_pull_source_titles(object())
