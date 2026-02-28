from __future__ import annotations

from dataclasses import dataclass
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


class _FakeSpreadsheet:
    def __init__(self) -> None:
        self.values_batch_update = Mock()


class _FakeClient:
    def __init__(self) -> None:
        self.worksheets = {
            "solicitudes": _FakeWorksheet("solicitudes"),
            "delegadas": _FakeWorksheet("delegadas"),
        }
        self.open_spreadsheet = Mock(return_value=_FakeSpreadsheet())
        self.get_worksheets_by_title = Mock(return_value=self.worksheets)
        self.get_worksheet = Mock(side_effect=lambda name: self.worksheets[name])
        self.read_all_values = Mock(side_effect=self._read_all_values)
        self.values_batch_update = Mock()
        self.clear = Mock()
        self.get_rows = Mock(return_value=[])

    def _read_all_values(self, worksheet_name: str) -> list[list[str]]:
        if worksheet_name == "solicitudes":
            return [HEADER_CANONICO_SOLICITUDES]
        if worksheet_name == "delegadas":
            return [["uuid", "nombre", "updated_at"]]
        return []


class _FakeRepository:
    def __init__(self) -> None:
        self.ensure_schema = Mock(return_value=[])


def _build_service(connection, *, client: _FakeClient | None = None) -> SheetsSyncService:
    return SheetsSyncService(
        connection=connection,
        config_store=_FakeConfigStore(SheetsConfig("sheet-id", "/tmp/creds.json", "device-x")),
        client=client or _FakeClient(),
        repository=_FakeRepository(),
    )


def test_flush_write_batches_ignores_empty_pending_buffers(connection) -> None:
    client = _FakeClient()
    spreadsheet = _FakeSpreadsheet()
    worksheet = client.worksheets["solicitudes"]
    service = _build_service(connection, client=client)

    service._flush_write_batches(spreadsheet, worksheet)

    client.values_batch_update.assert_not_called()


def test_flush_write_batches_executes_small_batches_once(connection) -> None:
    client = _FakeClient()
    spreadsheet = _FakeSpreadsheet()
    worksheet = client.worksheets["solicitudes"]
    service = _build_service(connection, client=client)

    service._pending_append_rows[worksheet.title] = [["uuid-1", "A"]]
    service._pending_batch_updates[worksheet.title] = [{"range": "A2:B2", "values": [["uuid-1", "B"]]}]
    service._pending_values_batch_updates[worksheet.title] = [{"range": "'solicitudes'!C2", "values": [["ok"]]}]

    service._flush_write_batches(spreadsheet, worksheet)

    client.values_batch_update.assert_called_once_with(
        {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": "'solicitudes'!A2:B2", "values": [["uuid-1", "A"]]},
                {"range": "A2:B2", "values": [["uuid-1", "B"]]},
                {"range": "'solicitudes'!C2", "values": [["ok"]]},
            ],
        }
    )


def test_push_solicitudes_with_no_rows_updates_header_only(connection) -> None:
    client = _FakeClient()
    spreadsheet = _FakeSpreadsheet()
    service = _build_service(connection, client=client)

    uploaded, conflicts, duplicates = service._push_solicitudes(spreadsheet, last_sync_at=None)

    assert (uploaded, conflicts, duplicates) == (0, 0, 0)
    client.worksheets["solicitudes"].update.assert_called_once_with("A1", [HEADER_CANONICO_SOLICITUDES])


def test_push_delegadas_single_batch_permission_error_propagates(connection, persona_id) -> None:
    client = _FakeClient()
    spreadsheet = _FakeSpreadsheet()
    service = _build_service(connection, client=client)
    client.values_batch_update.side_effect = SheetsPermissionError("Permiso denegado")

    cursor = connection.cursor()
    cursor.execute(
        "UPDATE personas SET uuid = ?, updated_at = ?, source_device = ? WHERE id = ?",
        ("delegada-uuid-1", "2026-01-01T10:00:00Z", "device-x", persona_id),
    )
    connection.commit()

    with pytest.raises(SheetsPermissionError, match="Permiso"):
        service._push_delegadas(spreadsheet, last_sync_at="2025-01-01T00:00:00Z")

    client.values_batch_update.assert_called_once()
