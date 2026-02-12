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
    def __init__(self, title: str, values: list[list[str]]) -> None:
        self.title = title
        self._values = values

    def get_all_values(self) -> list[list[str]]:
        return self._values

    def update(self, *_: Any, **__: Any) -> None:
        return None

    def append_row(self, *_: Any, **__: Any) -> None:
        return None


class _FakeSpreadsheet:
    def __init__(self, worksheets: dict[str, _FakeWorksheet]) -> None:
        self._worksheets = worksheets

    def worksheet(self, name: str) -> _FakeWorksheet:
        return self._worksheets[name]

    def batch_get(self, ranges: list[str]) -> list[list[list[str]]]:
        result: list[list[list[str]]] = []
        for range_name in ranges:
            worksheet_name = range_name.split("!", maxsplit=1)[0].strip("'")
            result.append(self._worksheets[worksheet_name].get_all_values())
        return result


class _FakeClient:
    def __init__(self, spreadsheet: _FakeSpreadsheet) -> None:
        self.spreadsheet = spreadsheet
        self.open_calls = 0
        self.read_calls_count = 0
        self._cache: dict[str, list[list[str]]] = {}

    def open_spreadsheet(self, _: Path, __: str) -> _FakeSpreadsheet:
        self.open_calls += 1
        self._cache.clear()
        return self.spreadsheet

    def get_worksheet_values_cached(self, name: str) -> list[list[str]]:
        if name in self._cache:
            return self._cache[name]
        self.read_calls_count += 1
        values = self.spreadsheet.worksheet(name).get_all_values()
        self._cache[name] = values
        return values

    def batch_get_ranges(self, ranges: list[str]) -> dict[str, list[list[str]]]:
        self.read_calls_count += 1
        values = self.spreadsheet.batch_get(ranges)
        result: dict[str, list[list[str]]] = {}
        for range_name, sheet_values in zip(ranges, values, strict=False):
            worksheet_name = range_name.split("!", maxsplit=1)[0].strip("'")
            result[worksheet_name] = sheet_values
            self._cache[worksheet_name] = sheet_values
        return result

    def reset_read_calls_count(self) -> None:
        self.read_calls_count = 0

    def get_read_calls_count(self) -> int:
        return self.read_calls_count


class _FakeRepository:
    def __init__(self) -> None:
        self.ensure_calls = 0

    def ensure_schema(self, *_: Any, **__: Any) -> list[str]:
        self.ensure_calls += 1
        return []


def _empty_sheet(name: str, headers: list[str]) -> _FakeWorksheet:
    return _FakeWorksheet(name, [headers])


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
            "delegadas": _empty_sheet("delegadas", ["uuid", "updated_at"]),
            "solicitudes": _FakeWorksheet("solicitudes", remote_duplicate),
            "cuadrantes": _empty_sheet("cuadrantes", ["uuid", "updated_at"]),
            "pdf_log": _empty_sheet("pdf_log", ["pdf_id", "updated_at"]),
            "config": _empty_sheet("config", ["key", "updated_at"]),
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


def test_sync_pull_reutiliza_persona_existente_y_no_rompe_unique_nombre(connection) -> None:
    delegadas_sheet = [
        [
            "uuid",
            "nombre",
            "genero",
            "bolsa_mes_min",
            "bolsa_anual_min",
            "activa",
            "updated_at",
            "source_device",
            "deleted",
        ],
        [
            "uuid-remoto-1",
            "Delegada Repetida",
            "F",
            "600",
            "7200",
            "1",
            "2025-01-20T10:00:00Z",
            "device-remote",
            "0",
        ],
        [
            "uuid-remoto-2",
            "Delegada Repetida",
            "F",
            "600",
            "7200",
            "1",
            "2025-01-20T11:00:00Z",
            "device-remote",
            "0",
        ],
        [
            "",
            "Delegada Repetida",
            "F",
            "600",
            "7200",
            "1",
            "2025-01-20T12:00:00Z",
            "device-remote",
            "0",
        ],
    ]

    spreadsheet = _FakeSpreadsheet(
        {
            "delegadas": _FakeWorksheet("delegadas", delegadas_sheet),
            "solicitudes": _empty_sheet("solicitudes", ["uuid", "updated_at"]),
            "cuadrantes": _empty_sheet("cuadrantes", ["uuid", "updated_at"]),
            "pdf_log": _empty_sheet("pdf_log", ["pdf_id", "updated_at"]),
            "config": _empty_sheet("config", ["key", "updated_at"]),
        }
    )
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
        repository=_FakeRepository(),
    )

    service.pull()
    service.pull()

    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM personas WHERE nombre = ?", ("Delegada Repetida",))
    total = cursor.fetchone()["total"]
    assert total == 1


def test_sync_bidirectional_reutiliza_open_y_cuenta_lecturas(connection) -> None:
    spreadsheet = _FakeSpreadsheet(
        {
            "delegadas": _empty_sheet("delegadas", ["uuid", "updated_at"]),
            "solicitudes": _empty_sheet("solicitudes", ["uuid", "updated_at"]),
            "cuadrantes": _empty_sheet("cuadrantes", ["uuid", "updated_at"]),
            "pdf_log": _empty_sheet("pdf_log", ["pdf_id", "updated_at"]),
            "config": _empty_sheet("config", ["key", "updated_at"]),
        }
    )
    client = _FakeClient(spreadsheet)
    service = SheetsSyncService(
        connection=connection,
        config_store=_FakeConfigStore(
            SheetsConfig(
                spreadsheet_id="sheet-id",
                credentials_path="/tmp/fake_credentials.json",
                device_id="device-local",
            )
        ),
        client=client,
        repository=_FakeRepository(),
    )

    service.sync_bidirectional()

    assert client.open_calls == 1
    assert client.read_calls_count <= 5
