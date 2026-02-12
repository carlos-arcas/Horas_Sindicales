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
    def __init__(self, values: list[list[str]], title: str | None = None) -> None:
        self._values = values
        self.title = title or ""

    def get_all_values(self) -> list[list[str]]:
        return self._values


class _FakeSpreadsheet:
    def __init__(self, worksheets: dict[str, _FakeWorksheet]) -> None:
        self._worksheets = worksheets
        for name, worksheet in worksheets.items():
            worksheet.title = name

    def worksheet(self, name: str) -> _FakeWorksheet:
        return self._worksheets[name]

    def worksheets(self) -> list[_FakeWorksheet]:
        return list(self._worksheets.values())


class _FakeClient:
    def __init__(self, spreadsheet: _FakeSpreadsheet) -> None:
        self.spreadsheet = spreadsheet
        self._cache: dict[str, list[list[str]]] = {}
        self._read_calls_count = 0

    def open_spreadsheet(self, _: Path, __: str) -> _FakeSpreadsheet:
        self._cache = {}
        self._read_calls_count = 0
        return self.spreadsheet

    def read_all_values(self, name: str) -> list[list[str]]:
        if name in self._cache:
            return self._cache[name]
        values = self.spreadsheet.worksheet(name).get_all_values()
        self._cache[name] = values
        self._read_calls_count += 1
        return values


    def get_worksheet_values_cached(self, name: str) -> list[list[str]]:
        return self.read_all_values(name)

    def get_worksheet(self, name: str) -> _FakeWorksheet:
        return self.spreadsheet.worksheet(name)

    def get_worksheets_by_title(self) -> dict[str, _FakeWorksheet]:
        return {ws.title: ws for ws in self.spreadsheet.worksheets()}

    def batch_get_ranges(self, ranges: list[str]) -> dict[str, list[list[str]]]:
        mapped: dict[str, list[list[str]]] = {}
        for range_name in ranges:
            worksheet_name = range_name.split("!", 1)[0].strip("'").replace("''", "'")
            mapped[range_name] = self.read_all_values(worksheet_name)
        if ranges:
            self._read_calls_count = max(0, self._read_calls_count - len(ranges) + 1)
        return mapped

    def get_read_calls_count(self) -> int:
        return self._read_calls_count

    def get_avoided_requests_count(self) -> int:
        return 0


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
            "delegadas": _FakeWorksheet(delegadas_sheet),
            "solicitudes": _empty_sheet(["uuid", "updated_at"]),
            "cuadrantes": _empty_sheet(["uuid", "updated_at"]),
            "pdf_log": _empty_sheet(["pdf_id", "updated_at"]),
            "config": _empty_sheet(["key", "updated_at"]),
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

def test_pull_solicitudes_resuelve_delegada_por_nombre(connection, persona_repo, persona_id) -> None:
    persona_uuid = persona_repo.get_or_create_uuid(persona_id)
    cursor = connection.cursor()
    cursor.execute("SELECT nombre FROM personas WHERE id = ?", (persona_id,))
    nombre = cursor.fetchone()["nombre"]

    solicitudes_sheet = [
        ["uuid", "delegada_uuid", "delegada_nombre", "fecha", "desde", "hasta", "completo", "horas", "notas", "updated_at"],
        ["sol-1", "", nombre, "2025-01-15", "09:00", "11:00", "0", "120", "importada", "2025-01-20T10:00:00Z"],
    ]

    spreadsheet = _FakeSpreadsheet(
        {
            "delegadas": _empty_sheet(["uuid", "updated_at"]),
            "solicitudes": _FakeWorksheet(solicitudes_sheet),
            "cuadrantes": _empty_sheet(["uuid", "updated_at"]),
            "pdf_log": _empty_sheet(["pdf_id", "updated_at"]),
            "config": _empty_sheet(["key", "updated_at"]),
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

    summary = service.pull()

    assert summary.inserted_local == 1
    assert summary.omitted_by_delegada == 0
    cursor.execute("SELECT s.uuid, p.uuid AS delegada_uuid FROM solicitudes s JOIN personas p ON p.id = s.persona_id WHERE s.uuid = ?", ("sol-1",))
    inserted = cursor.fetchone()
    assert inserted["delegada_uuid"] == persona_uuid


def test_pull_solicitudes_omite_huerfanas_sin_uuid_ni_nombre(connection) -> None:
    solicitudes_sheet = [
        ["uuid", "fecha", "desde", "hasta", "completo", "horas", "updated_at"],
        ["sol-huerfana", "2025-01-15", "09:00", "11:00", "0", "120", "2025-01-20T10:00:00Z"],
    ]

    spreadsheet = _FakeSpreadsheet(
        {
            "delegadas": _empty_sheet(["uuid", "updated_at"]),
            "solicitudes": _FakeWorksheet(solicitudes_sheet),
            "cuadrantes": _empty_sheet(["uuid", "updated_at"]),
            "pdf_log": _empty_sheet(["pdf_id", "updated_at"]),
            "config": _empty_sheet(["key", "updated_at"]),
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

    summary = service.pull()

    assert summary.inserted_local == 0
    assert summary.omitted_by_delegada == 1
    assert summary.errors == 1
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM solicitudes WHERE uuid = ?", ("sol-huerfana",))
    assert cursor.fetchone()["total"] == 0


def test_pull_solicitudes_con_cabecera_real_resuelve_por_columna_delegada(connection, persona_repo, persona_id) -> None:
    persona_uuid = persona_repo.get_or_create_uuid(persona_id)
    cursor = connection.cursor()
    cursor.execute("SELECT nombre FROM personas WHERE id = ?", (persona_id,))
    nombre = cursor.fetchone()["nombre"]

    solicitudes_sheet = [
        [
            "uuid",
            "delegada_uuid",
            "fecha",
            "desde_h",
            "desde_m",
            "hasta_h",
            "hasta_m",
            "completo",
            "minutos_total",
            "notas",
            "estado",
            "created_at",
            "updated_at",
            "source_device",
            "deleted",
            "pdf_id",
            "Delegada",
            "",
        ],
        [
            "sol-real-1",
            "",
            "15/01/2025",
            "9",
            "0",
            "11",
            "0",
            "0",
            "120",
            "importada",
            "historico",
            "2025-01-15",
            "2025-01-20T10:00:00Z",
            "device-remote",
            "0",
            "",
            f"  {nombre}  ",
            "valor-ignorado",
        ],
    ]

    spreadsheet = _FakeSpreadsheet(
        {
            "delegadas": _empty_sheet(["uuid", "updated_at"]),
            "solicitudes": _FakeWorksheet(solicitudes_sheet),
            "cuadrantes": _empty_sheet(["uuid", "updated_at"]),
            "pdf_log": _empty_sheet(["pdf_id", "updated_at"]),
            "config": _empty_sheet(["key", "updated_at"]),
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

    summary = service.pull()

    assert summary.inserted_local == 1
    assert summary.omitidas_por_delegada == 0

    cursor.execute(
        """
        SELECT s.uuid, p.uuid AS delegada_uuid, s.fecha_pedida, s.desde_min, s.hasta_min
        FROM solicitudes s
        JOIN personas p ON p.id = s.persona_id
        WHERE s.uuid = ?
        """,
        ("sol-real-1",),
    )
    inserted = cursor.fetchone()
    assert inserted["delegada_uuid"] == persona_uuid
    assert inserted["fecha_pedida"] == "2025-01-15"
    assert inserted["desde_min"] == 540
    assert inserted["hasta_min"] == 660


def test_pull_solicitudes_omite_si_delegada_no_resuelve_por_nombre(connection) -> None:
    solicitudes_sheet = [
        ["uuid", "delegada_uuid", "Delegada", "fecha", "desde_h", "desde_m", "hasta_h", "hasta_m", "completo", "minutos_total", "updated_at"],
        ["sol-no-match", "", "Delegada Inexistente", "2025-01-15", "9", "0", "11", "0", "0", "120", "2025-01-20T10:00:00Z"],
    ]

    spreadsheet = _FakeSpreadsheet(
        {
            "delegadas": _empty_sheet(["uuid", "updated_at"]),
            "solicitudes": _FakeWorksheet(solicitudes_sheet),
            "cuadrantes": _empty_sheet(["uuid", "updated_at"]),
            "pdf_log": _empty_sheet(["pdf_id", "updated_at"]),
            "config": _empty_sheet(["key", "updated_at"]),
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

    summary = service.pull()

    assert summary.inserted_local == 0
    assert summary.omitidas_por_delegada == 1
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM solicitudes WHERE uuid = ?", ("sol-no-match",))
    assert cursor.fetchone()["total"] == 0
