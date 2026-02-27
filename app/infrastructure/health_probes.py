from __future__ import annotations

import socket
import time
from pathlib import Path
from typing import Callable

from app.application.sheets_service import SHEETS_SCHEMA
from app.domain.ports import SheetsClientPort, SheetsConfigStorePort, SqlConnectionPort

_SYNC_ACTION = "open_sync_settings"


def _base_missing_config_result() -> dict[str, tuple[bool, str, str]]:
    return {
        "credentials": (False, "Falta configurar credenciales.", _SYNC_ACTION),
        "spreadsheet": (False, "Falta configurar Spreadsheet ID.", _SYNC_ACTION),
        "worksheet": (False, "No se puede validar hojas sin configuración.", _SYNC_ACTION),
        "headers": (False, "No se puede validar cabeceras sin configuración.", _SYNC_ACTION),
    }


def _base_config_result(credentials_ok: bool, spreadsheet_ok: bool) -> dict[str, tuple[bool, str, str]]:
    return {
        "credentials": (
            credentials_ok,
            "Credenciales presentes y legibles." if credentials_ok else "Credenciales ausentes o no accesibles.",
            _SYNC_ACTION,
        ),
        "spreadsheet": (
            spreadsheet_ok,
            "Spreadsheet ID configurado." if spreadsheet_ok else "Falta Spreadsheet ID.",
            _SYNC_ACTION,
        ),
    }


def _pending_remote_validation_result(
    base_result: dict[str, tuple[bool, str, str]],
) -> dict[str, tuple[bool, str, str]]:
    base_result["worksheet"] = (False, "No se puede validar la hoja todavía.", _SYNC_ACTION)
    base_result["headers"] = (False, "No se puede validar cabeceras todavía.", _SYNC_ACTION)
    return base_result


def _worksheet_result(worksheets: dict[str, object]) -> tuple[bool, str, str]:
    missing = [name for name in ("delegadas", "solicitudes", "cuadrantes") if name not in worksheets]
    message = "Todas las worksheets esperadas existen." if not missing else f"Faltan worksheets: {', '.join(missing)}."
    return (not missing, message, _SYNC_ACTION)


def _headers_result(worksheets: dict[str, object], header_row: list[str]) -> tuple[bool, str, str]:
    if "solicitudes" not in worksheets:
        return (True, "Cabeceras principales detectadas.", _SYNC_ACTION)

    current_headers = [cell.strip().lower() for cell in header_row]
    expected = SHEETS_SCHEMA["solicitudes"]
    missing_headers = [head for head in expected if head not in current_headers]
    if missing_headers:
        return (False, f"Faltan cabeceras en solicitudes: {', '.join(missing_headers[:4])}.", _SYNC_ACTION)
    return (True, "Cabeceras principales detectadas.", _SYNC_ACTION)


def _remote_validation_error_result(exc: Exception) -> dict[str, tuple[bool, str, str]]:
    return {
        "worksheet": (False, f"No se pudo acceder al Spreadsheet: {exc}", _SYNC_ACTION),
        "headers": (False, "No se pudo validar rango/cabeceras.", _SYNC_ACTION),
    }


class SheetsConfigProbe:
    def __init__(self, config_store: SheetsConfigStorePort, sheets_client: SheetsClientPort) -> None:
        self._config_store = config_store
        self._sheets_client = sheets_client

    def check(self) -> dict[str, tuple[bool, str, str]]:
        config = self._config_store.load()
        if not config:
            return _base_missing_config_result()

        credentials_ok = bool(config.credentials_path and Path(config.credentials_path).exists())
        spreadsheet_ok = bool(config.spreadsheet_id)
        result = _base_config_result(credentials_ok, spreadsheet_ok)

        if not credentials_ok or not spreadsheet_ok:
            return _pending_remote_validation_result(result)

        try:
            self._sheets_client.open_spreadsheet(Path(config.credentials_path), config.spreadsheet_id)
            worksheets = self._sheets_client.get_worksheets_by_title()
            header_row = self._load_solicitudes_header_row(worksheets)
            result["worksheet"] = _worksheet_result(worksheets)
            result["headers"] = _headers_result(worksheets, header_row)
            return result
        except Exception as exc:  # noqa: BLE001
            result.update(_remote_validation_error_result(exc))
            return result

    def _load_solicitudes_header_row(self, worksheets: dict[str, object]) -> list[str]:
        if "solicitudes" not in worksheets:
            return []
        values = self._sheets_client.read_all_values("solicitudes")
        return values[0] if values else []


class DefaultConnectivityProbe:
    def check(self, *, timeout_seconds: float = 3.0) -> tuple[bool, bool, float | None, str]:
        internet_ok = False
        api_reachable = False
        latency_ms: float | None = None
        started = time.perf_counter()
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=timeout_seconds).close()
            internet_ok = True
        except OSError:
            internet_ok = False

        try:
            conn = socket.create_connection(("sheets.googleapis.com", 443), timeout=timeout_seconds)
            conn.close()
            api_reachable = True
            latency_ms = (time.perf_counter() - started) * 1000
        except OSError:
            api_reachable = False

        if latency_ms is None:
            return internet_ok, api_reachable, None, "Latencia no disponible (sin conexión API)."
        return internet_ok, api_reachable, latency_ms, f"Latencia aproximada API: {latency_ms:.0f} ms."


class SQLiteLocalDbProbe:
    def __init__(self, connection_factory: Callable[[], SqlConnectionPort], migrations_total: int = 3) -> None:
        self._connection_factory = connection_factory
        self._migrations_total = migrations_total

    def check(self) -> dict[str, tuple[bool, str, str]]:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            db_ok = cursor.fetchone() is not None

            cursor.execute("SELECT COUNT(*) AS total FROM schema_migrations")
            migrations_applied = int(cursor.fetchone()["total"])
            migrations_ok = migrations_applied >= self._migrations_total

            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM solicitudes
                WHERE generated = 0
                  AND (deleted = 0 OR deleted IS NULL)
                  AND pdf_path IS NOT NULL
                  AND TRIM(pdf_path) <> ''
                """
            )
            ghost_pending = int(cursor.fetchone()["total"])
            ghost_ok = ghost_pending == 0
        except Exception as exc:  # noqa: BLE001
            return {
                "local_db": (False, f"Base de datos no accesible: {exc}", "open_db_help"),
                "migrations": (False, "No se pudo validar estado de migraciones.", "open_db_help"),
                "ghost_pending": (False, "No se pudo validar pendientes fantasma.", "open_sync_panel"),
            }
        finally:
            if hasattr(connection, "close"):
                connection.close()

        return {
            "local_db": (db_ok, "Base de datos local accesible.", "open_db_help"),
            "migrations": (
                migrations_ok,
                "Migraciones al día." if migrations_ok else "Hay migraciones pendientes.",
                "open_db_help",
            ),
            "ghost_pending": (
                ghost_ok,
                "No se detectan pendientes fantasma."
                if ghost_ok
                else f"Se detectaron {ghost_pending} pendientes fantasma.",
                "open_sync_panel",
            ),
        }
