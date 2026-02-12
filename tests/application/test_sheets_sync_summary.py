from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.domain.models import SheetsConfig, Solicitud
from app.domain.sync_models import SyncSummary


@dataclass
class _FakeConfigStore:
    config: SheetsConfig

    def load(self) -> SheetsConfig:
        return self.config


class _FakeWorksheet:
    def __init__(self, values: list[list[str]], title: str = "") -> None:
        self._values = values
        self.title = title

    def get_all_values(self) -> list[list[str]]:
        return self._values



class _FakeSpreadsheet:
    def __init__(self, worksheets: dict[str, _FakeWorksheet]) -> None:
        self._worksheets = worksheets
        self.worksheet_calls = 0
        for name, worksheet in worksheets.items():
            if not getattr(worksheet, "title", ""):
                worksheet.title = name

    def worksheet(self, name: str) -> _FakeWorksheet:
        self.worksheet_calls += 1
        return self._worksheets[name]

    def worksheets(self) -> list[_FakeWorksheet]:
        return list(self._worksheets.values())


class _FakeClient:
    def __init__(self, spreadsheet: _FakeSpreadsheet) -> None:
        self.spreadsheet = spreadsheet
        self.open_calls = 0

    def open_spreadsheet(self, _: Path, __: str) -> _FakeSpreadsheet:
        self.open_calls += 1
        return self.spreadsheet


class _FakeRepository:
    def __init__(self) -> None:
        self.ensure_calls = 0

    def ensure_schema(self, *_: Any, **__: Any) -> list[str]:
        self.ensure_calls += 1
        return []


def _empty_sheet(headers: list[str], title: str = "") -> _FakeWorksheet:
    return _FakeWorksheet([headers], title=title)


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


def test_sync_bidirectional_usa_misma_spreadsheet(connection) -> None:
    spreadsheet = _FakeSpreadsheet({})
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

    service.pull = lambda spreadsheet=None: SyncSummary(inserted_local=0)  # type: ignore[method-assign]
    service.push = lambda spreadsheet=None: SyncSummary(inserted_remote=0)  # type: ignore[method-assign]

    service.sync_bidirectional()

    assert client.open_calls == 1


def test_pull_reutiliza_worksheet_en_cache(connection) -> None:
    delegadas = _FakeWorksheet([["uuid", "nombre", "updated_at", "source_device", "deleted"], ["", "", "", "", ""]], title="delegadas")
    solicitudes = _FakeWorksheet([["uuid", "updated_at"]], title="solicitudes")
    spreadsheet = _FakeSpreadsheet(
        {
            "delegadas": delegadas,
            "solicitudes": solicitudes,
            "cuadrantes": _empty_sheet(["uuid", "updated_at"], title="cuadrantes"),
            "pdf_log": _empty_sheet(["pdf_id", "updated_at"], title="pdf_log"),
            "config": _empty_sheet(["key", "updated_at"], title="config"),
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

    # Sin caché, las llamadas a worksheet() crecen por cada acceso repetido a nombres iguales.
    assert spreadsheet.worksheet_calls <= 5
