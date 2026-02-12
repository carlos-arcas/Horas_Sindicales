from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.domain.models import SheetsConfig, Solicitud


@dataclass
class _FakeConfigStore:
    config: SheetsConfig

    def load(self) -> SheetsConfig:
        return self.config


class _FakeWorksheet:
    def __init__(self, values: list[list[str]]) -> None:
        self._values = values

    def get_all_values(self) -> list[list[str]]:
        return self._values


class _FakeSpreadsheet:
    def __init__(self, worksheets: dict[str, _FakeWorksheet]) -> None:
        self._worksheets = worksheets

    def worksheet(self, name: str) -> _FakeWorksheet:
        return self._worksheets[name]


class _FakeClient:
    def __init__(self, spreadsheet: _FakeSpreadsheet) -> None:
        self.spreadsheet = spreadsheet

    def open_spreadsheet(self, _: Path, __: str) -> _FakeSpreadsheet:
        return self.spreadsheet


class _FakeRepository:
    def __init__(self) -> None:
        self.ensure_calls = 0

    def ensure_schema(self, *_: Any, **__: Any) -> list[str]:
        self.ensure_calls += 1
        return []


def _empty_sheet(headers: list[str]) -> _FakeWorksheet:
    return _FakeWorksheet([headers])


def test_sync_pull_omite_duplicados_y_devuelve_summary(connection, persona_repo, solicitud_repo, persona_id) -> None:
    persona_uuid = persona_repo.get_or_create_uuid(persona_id)
    solicitud_repo.create(
        Solicitud(
            id=None,
            persona_id=persona_id,
            fecha_solicitud="2025-01-01",
            fecha_pedida="2025-01-15",
            desde_min=540,
            hasta_min=660,
            completo=False,
            horas_solicitadas_min=120,
            observaciones="local",
            notas="local",
        )
    )

    remote_duplicate = [
        [
            "uuid",
            "delegada_uuid",
            "fecha",
            "completo",
            "minutos_total",
            "desde_h",
            "desde_m",
            "hasta_h",
            "hasta_m",
            "updated_at",
            "source_device",
        ],
        [
            "remote-uuid-1",
            persona_uuid,
            "2025-01-15",
            "0",
            "120",
            "09:00",
            "",
            "11:00",
            "",
            "2025-01-20T10:00:00Z",
            "device-remote",
        ],
    ]

    spreadsheet = _FakeSpreadsheet(
        {
            "delegadas": _empty_sheet(["uuid", "updated_at"]),
            "solicitudes": _FakeWorksheet(remote_duplicate),
            "cuadrantes": _empty_sheet(["uuid", "updated_at"]),
            "pdf_log": _empty_sheet(["pdf_id", "updated_at"]),
            "config": _empty_sheet(["key", "updated_at"]),
        }
    )
    repository = _FakeRepository()
    service = SheetsSyncService(
        connection=connection,
        config_store=_FakeConfigStore(
            SheetsConfig(
                spreadsheet_id="sheet-id",
                credentials_path="/tmp/fake_credentials.json",
                device_id="device-local",
            )
        ),
        client=_FakeClient(spreadsheet),
        repository=repository,
    )

    summary = service.pull()

    assert summary.downloaded == 0
    assert summary.conflicts == 0
    assert summary.omitted_duplicates == 1
    assert summary.uploaded == 0
    assert repository.ensure_calls == 1
