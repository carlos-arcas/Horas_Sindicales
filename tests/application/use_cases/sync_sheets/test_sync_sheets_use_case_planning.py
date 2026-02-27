from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

import pytest

from app.application.use_cases.sync_sheets import HEADER_CANONICO_SOLICITUDES, SheetsSyncService
from app.domain.models import SheetsConfig
from app.domain.sheets_errors import SheetsPermissionError


@dataclass
class _FakeConfigStore:
    config: SheetsConfig | None

    def load(self) -> SheetsConfig | None:
        return self.config


class _FakeWorksheet:
    def __init__(self, title: str) -> None:
        self.title = title
        self.update = Mock()
        self.resize = Mock()
        self.append_rows = Mock()
        self.batch_update = Mock()


class _FakeClient:
    def __init__(self) -> None:
        self.worksheets = {
            "solicitudes": _FakeWorksheet("solicitudes"),
            "delegadas": _FakeWorksheet("delegadas"),
        }
        self.open_spreadsheet = Mock(return_value=object())
        self.get_worksheets_by_title = Mock(return_value=self.worksheets)
        self.get_worksheet = Mock(side_effect=lambda name: self.worksheets[name])
        self.read_all_values = Mock(side_effect=self._read_all_values)
        self.append_rows = Mock()
        self.clear = Mock()
        self.get_rows = Mock(return_value=[])

    def _read_all_values(self, worksheet_name: str) -> list[list[Any]]:
        if worksheet_name == "solicitudes":
            return [HEADER_CANONICO_SOLICITUDES]
        if worksheet_name == "delegadas":
            return [["uuid", "nombre", "updated_at"]]
        return []


class _FakeRepository:
    def __init__(self) -> None:
        self.ensure_schema = Mock(return_value=[])


def _build_service(connection, *, client: _FakeClient | None = None, repository: _FakeRepository | None = None) -> SheetsSyncService:
    return SheetsSyncService(
        connection=connection,
        config_store=_FakeConfigStore(SheetsConfig("sheet-id", "/tmp/creds.json", "dev-1")),
        client=client or _FakeClient(),
        repository=repository or _FakeRepository(),
    )


def test_simulate_sync_plan_without_changes_returns_header_only(connection) -> None:
    service = _build_service(connection)

    plan = service.simulate_sync_plan()

    assert plan.worksheet == "solicitudes"
    assert plan.to_create == ()
    assert plan.to_update == ()
    assert plan.unchanged == ()
    assert plan.conflicts == ()
    assert plan.potential_errors == ()
    assert plan.values_matrix == (tuple(HEADER_CANONICO_SOLICITUDES),)


def test_ensure_connection_ready_propagates_permission_error(connection) -> None:
    client = _FakeClient()
    repository = _FakeRepository()
    client.open_spreadsheet.side_effect = SheetsPermissionError("Sin permisos de escritura")
    service = _build_service(connection, client=client, repository=repository)

    with pytest.raises(SheetsPermissionError, match="Sin permisos"):
        service.ensure_connection()

    repository.ensure_schema.assert_not_called()

def test_insert_solicitud_from_remote_uses_conflict_resolution_service_mock(connection, monkeypatch) -> None:
    service = _build_service(connection)

    monkeypatch.setattr(
        "app.application.use_cases.sync_sheets.use_case.get_or_resolve_delegada_uuid",
        Mock(return_value=None),
    )

    written, omitted_delegada, errors = service._insert_solicitud_from_remote(
        "sol-uuid-1",
        {
            "delegada_uuid": "",
            "Delegada": "Delegada No Resuelta",
            "fecha": "2026-02-01",
            "desde_h": "09",
            "desde_m": "00",
            "hasta_h": "10",
            "hasta_m": "00",
            "completo": 0,
            "minutos_total": 60,
        },
    )

    assert (written, omitted_delegada, errors) == (False, 1, 1)
