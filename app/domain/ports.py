from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, Iterable

from app.domain.sync_models import SyncExecutionPlan, SyncSummary
from app.domain.models import GrupoConfig, Persona, SheetsConfig, Solicitud


class PersonaRepository(Protocol):
    def list_all(self, include_inactive: bool = False) -> Iterable[Persona]:
        ...

    def get_by_id(self, persona_id: int) -> Persona | None:
        ...

    def get_by_nombre(self, nombre: str) -> Persona | None:
        ...

    def create(self, persona: Persona) -> Persona:
        ...

    def update(self, persona: Persona) -> Persona:
        ...

    def get_or_create_uuid(self, persona_id: int) -> str | None:
        ...


class CuadranteRepository(Protocol):
    def exists_for_delegada(self, delegada_uuid: str, dia_semana: str) -> bool:
        ...

    def create(self, delegada_uuid: str, dia_semana: str, man_min: int, tar_min: int) -> None:
        ...


class SolicitudRepository(Protocol):
    def list_by_persona(self, persona_id: int) -> Iterable[Solicitud]:
        ...

    def list_by_persona_and_period(
        self, persona_id: int, year: int, month: int | None = None
    ) -> Iterable[Solicitud]:
        ...

    def list_by_persona_and_fecha(self, persona_id: int, fecha_pedida: str) -> Iterable[Solicitud]:
        ...

    def list_pendientes_by_persona(self, persona_id: int) -> Iterable[Solicitud]:
        ...

    def list_pendientes_all(self) -> Iterable[Solicitud]:
        ...

    def list_pendientes_huerfanas(self) -> Iterable[Solicitud]:
        ...

    def get_by_id(self, solicitud_id: int) -> Solicitud | None:
        ...

    def exists_duplicate(
        self,
        persona_id: int,
        fecha_pedida: str,
        desde_min: int | None,
        hasta_min: int | None,
        completo: bool,
    ) -> bool:
        ...

    def find_duplicate(
        self,
        persona_id: int,
        fecha_pedida: str,
        desde_min: int | None,
        hasta_min: int | None,
        completo: bool,
    ) -> Solicitud | None:
        ...

    def create(self, solicitud: Solicitud) -> Solicitud:
        ...

    def update_pdf_info(self, solicitud_id: int, pdf_path: str, pdf_hash: str | None) -> None:
        ...

    def mark_generated(self, solicitud_id: int, generated: bool = True) -> None:
        ...

    def delete(self, solicitud_id: int) -> None:
        ...

    def delete_by_ids(self, solicitud_ids: Iterable[int]) -> None:
        ...


class GrupoConfigRepository(Protocol):
    def get(self) -> GrupoConfig | None:
        ...

    def upsert(self, config: GrupoConfig) -> GrupoConfig:
        ...




class SqlCursorPort(Protocol):
    def execute(self, sql: str, params: tuple[object, ...] = ...) -> Any:
        ...

    def fetchone(self) -> Any:
        ...

    def fetchall(self) -> list[Any]:
        ...


class SqlConnectionPort(Protocol):
    def cursor(self) -> SqlCursorPort:
        ...

    def commit(self) -> None:
        ...

class SheetsConfigStorePort(Protocol):
    def load(self) -> SheetsConfig | None:
        ...

    def save(self, config: SheetsConfig) -> SheetsConfig:
        ...

    def credentials_path(self) -> Path:
        ...


class SheetsGatewayPort(Protocol):
    def test_connection(self, config: SheetsConfig, schema: dict[str, list[str]]) -> tuple[str, str, list[str]]:
        ...

    def read_personas(self, config: SheetsConfig) -> list[tuple[int, dict[str, Any]]]:
        ...

    def read_solicitudes(self, config: SheetsConfig) -> list[tuple[int, dict[str, Any]]]:
        ...

    def upsert_persona(self, config: SheetsConfig, row: dict[str, Any]) -> None:
        ...

    def upsert_solicitud(self, config: SheetsConfig, row: dict[str, Any]) -> None:
        ...

    def backfill_uuid(self, config: SheetsConfig, worksheet_name: str, row_index: int, uuid_value: str) -> None:
        ...


class SheetsClientPort(Protocol):
    def open_spreadsheet(self, credentials_path: Path, spreadsheet_id: str):
        ...

    def read_all_values(self, worksheet_name: str) -> list[list[str]]:
        ...

    def get_worksheet(self, name: str):
        ...

    def get_worksheets_by_title(self) -> dict[str, Any]:
        ...

    def batch_get_ranges(self, ranges: list[str]) -> dict[str, list[list[str]]]:
        ...

    def get_read_calls_count(self) -> int:
        ...

    def get_avoided_requests_count(self) -> int:
        ...

    def get_write_calls_count(self) -> int:
        ...

    def append_rows(self, worksheet_name: str, rows: list[list[Any]]) -> None:
        ...

    def batch_update(self, worksheet_name: str, data: list[dict[str, Any]]) -> None:
        ...

    def values_batch_update(self, body: dict[str, Any]) -> None:
        ...


class SheetsRepositoryPort(Protocol):
    def ensure_schema(self, spreadsheet, schema: dict[str, list[str]]) -> list[str]:
        ...


class SheetsConnectivityProbe(Protocol):
    def check(self, *, timeout_seconds: float = 3.0) -> tuple[bool, bool, float | None, str]:
        """Retorna: internet_ok, api_reachable, latency_ms, mensaje."""


class SheetsSchemaProbe(Protocol):
    def check(self) -> dict[str, tuple[bool, str, str]]:
        """Retorna un mapa clave->(ok, mensaje, action_id) para checks de configuración remota."""


class LocalDbProbe(Protocol):
    def check(self) -> dict[str, tuple[bool, str, str]]:
        """Retorna un mapa clave->(ok, mensaje, action_id) para checks de integridad local."""


class SheetsSyncPort(Protocol):
    def pull(self) -> SyncSummary:
        ...

    def push(self) -> SyncSummary:
        ...

    def sync(self) -> SyncSummary:
        ...

    def sync_bidirectional(self) -> SyncSummary:
        ...

    def simulate_sync_plan(self) -> SyncExecutionPlan:
        ...

    def execute_sync_plan(self, plan: SyncExecutionPlan) -> SyncSummary:
        ...

    def get_last_sync_at(self) -> str | None:
        ...

    def is_configured(self) -> bool:
        ...

    def store_sync_config_value(self, key: str, value: str) -> None:
        ...

    def register_pdf_log(self, persona_id: int, fechas: list[str], pdf_hash: str | None) -> None:
        ...


SheetsConfigRepository = SheetsConfigStorePort


# Puertos nominales para adaptadores SQLite.
SQLitePersonaRepositoryPort = PersonaRepository
SQLiteSolicitudRepositoryPort = SolicitudRepository
SQLiteGrupoConfigRepositoryPort = GrupoConfigRepository
SQLiteCuadranteRepositoryPort = CuadranteRepository
