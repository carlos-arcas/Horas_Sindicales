from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.errors import InfraError
from app.application.sheets_service import SHEETS_SCHEMA
from app.domain.sheets_errors import (
    SheetsConfigError,
    SheetsPermissionError,
    SheetsRateLimitError,
    construir_mensaje_permiso_sheets,
)
from app.application.dtos.sync_preflight_result import SyncPreflightResult
from app.domain.sync_models import SyncSummary
from app.application.use_cases.sync_sheets.sync_snapshots import (
    build_pdf_log_payload,
    format_rango_fechas,
    pdf_log_insert_values,
    pdf_log_update_values,
)

logger = logging.getLogger(__name__)


class OrquestadorPreflightSync:
        def preflight_permisos_escritura(self, spreadsheet: Any | None = None) -> SyncPreflightResult:
            if not hasattr(self._client, "check_write_access"):
                return SyncPreflightResult.ok_result()
            try:
                self._client.check_write_access("solicitudes")
                return SyncPreflightResult.ok_result()
            except SheetsPermissionError as error:
                enriched = self._enrich_permission_error(error, spreadsheet)
                return SyncPreflightResult.permission_denied(
                    mensaje=str(enriched),
                    accion_sugerida=construir_mensaje_permiso_sheets(enriched),
                    metadata=enriched.to_safe_payload(),
                )

        def _resolver_preflight_denegado(self, preflight: SyncPreflightResult) -> SyncSummary:
            if self._strict_sync_exceptions_enabled():
                raise self._build_permission_error(preflight)
            self._registrar_issue_preflight(preflight)
            self._log_sync_stats("push")
            return SyncSummary(errors=1)

        @staticmethod
        def _strict_sync_exceptions_enabled() -> bool:
            return os.getenv("SYNC_STRICT_EXCEPTIONS", "").strip().lower() == "true"

        def _build_permission_error(self, preflight: SyncPreflightResult) -> SheetsPermissionError:
            issue = preflight.issues[0]
            return SheetsPermissionError(
                issue.mensaje,
                spreadsheet_id=issue.metadata.get("spreadsheet_id"),
                worksheet=issue.metadata.get("worksheet"),
                service_account_email=issue.metadata.get("service_account_email"),
            )

        def _registrar_issue_preflight(self, preflight: SyncPreflightResult) -> None:
            issue = preflight.issues[0]
            logger.warning(
                "Preflight de sync bloqueó escritura: tipo=%s accion=%s metadata=%s",
                issue.tipo,
                issue.accion_sugerida,
                issue.metadata,
            )

        def _enrich_permission_error(self, error: SheetsPermissionError, spreadsheet: Any | None = None) -> SheetsPermissionError:
            spreadsheet_id = getattr(spreadsheet, "id", None)
            return error.with_context(spreadsheet_id=spreadsheet_id, worksheet="solicitudes")

        def store_sync_config_value(self, key: str, value: str) -> None:
            if not self.is_configured():
                return
            cursor = self._connection.cursor()
            now_iso = self._now_iso()
            cursor.execute(
                """
                INSERT INTO sync_config (key, value, updated_at, source_device)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at,
                    source_device = excluded.source_device
                """,
                (key, value, now_iso, self._device_id()),
            )
            self._connection.commit()

        def register_pdf_log(self, persona_id: int, fechas: list[str], pdf_hash: str | None) -> None:
            if not pdf_hash:
                return
            cursor = self._connection.cursor()
            cursor.execute("SELECT uuid FROM personas WHERE id = ?", (persona_id,))
            row = cursor.fetchone()
            if not row:
                return
            delegada_uuid = row["uuid"]
            rango = format_rango_fechas(fechas)
            now_iso = self._now_iso()
            cursor.execute(
                """
                INSERT INTO pdf_log (pdf_id, delegada_uuid, rango_fechas, fecha_generacion, hash, updated_at, source_device)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pdf_id) DO UPDATE SET
                    delegada_uuid = excluded.delegada_uuid,
                    rango_fechas = excluded.rango_fechas,
                    fecha_generacion = excluded.fecha_generacion,
                    hash = excluded.hash,
                    updated_at = excluded.updated_at,
                    source_device = excluded.source_device
                """,
                (
                    pdf_hash,
                    delegada_uuid,
                    rango,
                    now_iso,
                    pdf_hash,
                    now_iso,
                    self._device_id(),
                ),
            )
            self._connection.commit()

        def _prepare_sync_context(self, spreadsheet: Any) -> None:
            self._worksheet_cache = {}
            try:
                self._worksheet_cache.update(self._client.get_worksheets_by_title())
            except SheetsRateLimitError:
                raise
            except InfraError:
                logger.debug("No se pudo precargar metadata de worksheets; se continuará bajo demanda.", exc_info=True)

        def _get_worksheet(self, spreadsheet: Any, worksheet_name: str) -> Any:
            if worksheet_name in self._worksheet_cache:
                return self._worksheet_cache[worksheet_name]
            worksheet = self._client.get_worksheet(worksheet_name)
            self._worksheet_cache[worksheet_name] = worksheet
            return worksheet

        def _ensure_connection_ready(self) -> Any:
            spreadsheet = self._open_spreadsheet()
            self._prepare_sync_context(spreadsheet)
            self._repository.ensure_schema(spreadsheet, SHEETS_SCHEMA)
            return spreadsheet

        def _open_spreadsheet(self) -> Any:
            config = self._config_store.load()
            if not config or not config.spreadsheet_id or not config.credentials_path:
                raise SheetsConfigError("No hay configuración de Google Sheets.")
            credentials_path = Path(config.credentials_path)
            spreadsheet = self._client.open_spreadsheet(credentials_path, config.spreadsheet_id)
            return spreadsheet

        def _get_last_sync_at(self) -> str | None:
            cursor = self._connection.cursor()
            try:
                cursor.execute("SELECT last_sync_at FROM sync_state WHERE id = 1")
            except Exception as exc:
                # CI y pruebas aisladas pueden inicializar una conexión sin migraciones.
                # Devolvemos None para mantener la app operativa sin romper el arranque.
                if "no such table: sync_state" in str(exc).lower():
                    logger.warning("sync_state table missing; returning empty last_sync_at")
                    return None
                raise
            row = cursor.fetchone()
            if not row:
                return None
            return row["last_sync_at"]

        def _set_last_sync_at(self, timestamp: str) -> None:
            cursor = self._connection.cursor()
            cursor.execute(
                "UPDATE sync_state SET last_sync_at = ? WHERE id = 1",
                (timestamp,),
            )
            self._connection.commit()

        def _log_sync_stats(self, operation: str) -> None:
            read_count = self._client.get_read_calls_count() if hasattr(self._client, "get_read_calls_count") else "n/a"
            write_count = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else "n/a"
            avoided = self._client.get_avoided_requests_count() if hasattr(self._client, "get_avoided_requests_count") else "n/a"
            api_calls = self._client.get_sheets_api_calls_count() if hasattr(self._client, "get_sheets_api_calls_count") else "n/a"
            logger.info(
                "Sync stats (%s): api_calls=%s read_count=%s write_count=%s avoided_requests=%s",
                operation,
                api_calls,
                read_count,
                write_count,
                avoided,
            )

        @staticmethod
        def _now_iso() -> str:
            return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        def _device_id(self) -> str:
            config = self._config_store.load()
            return config.device_id if config else ""

        def _apply_config_value(self, key: str, value: Any) -> None:
            if key != "pdf_text":
                return
            cursor = self._connection.cursor()
            cursor.execute(
                """
                UPDATE grupo_config
                SET pdf_intro_text = ?
                WHERE id = 1
                """,
                (value or "",),
            )

        @staticmethod
        def _generate_uuid() -> str:
            return str(uuid.uuid4())
