from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from app.application.sheets_service import SHEETS_SCHEMA
from app.core.errors import InfraError
from app.application.delegada_resolution import get_or_resolve_delegada_uuid
from app.application.sync_normalization import normalize_hhmm, solicitud_unique_key
from app.application.use_cases import sync_sheets_core
from app.application.use_cases.sync_sheets.executor import execute_plan
from app.application.use_cases.sync_sheets.helpers import (
    build_solicitudes_sync_plan,
    sync_local_cuadrantes_from_personas,
)
from app.application.use_cases.sync_sheets.planner import build_plan
from app.application.use_cases.sync_sheets.sync_sheets_helpers import (
    execute_with_validation,
    rowcol_to_a1,
    rows_with_index,
)
from app.domain.ports import (
    SheetsClientPort,
    SheetsConfigStorePort,
    SheetsRepositoryPort,
    SqlConnectionPort,
)
from app.domain.sheets_errors import SheetsConfigError, SheetsRateLimitError
from app.domain.sync_models import SyncExecutionPlan, SyncSummary

logger = logging.getLogger(__name__)


HEADER_CANONICO_SOLICITUDES = ["uuid", "delegada_uuid", "delegada_nombre", "fecha", "desde_h", "desde_m", "hasta_h", "hasta_m", "completo", "minutos_total", "notas", "estado", "created_at", "updated_at", "source_device", "deleted", "pdf_id"]


class SheetsSyncService:
    def __init__(
        self,
        connection: SqlConnectionPort,
        config_store: SheetsConfigStorePort,
        client: SheetsClientPort,
        repository: SheetsRepositoryPort,
        *,
        enable_backfill: bool = False,
    ) -> None:
        self._connection = connection
        self._config_store = config_store
        self._client = client
        self._repository = repository
        self._worksheet_cache: dict[str, Any] = {}
        self._pending_append_rows: dict[str, list[list[Any]]] = {}
        self._pending_batch_updates: dict[str, list[dict[str, Any]]] = {}
        self._pending_values_batch_updates: dict[str, list[dict[str, Any]]] = {}
        self._enable_backfill = enable_backfill

    def pull(self) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        summary = self._pull_with_spreadsheet(spreadsheet)
        self._log_sync_stats("pull")
        return summary

    def push(self) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        summary = self._push_with_spreadsheet(spreadsheet)
        self._log_sync_stats("push")
        return summary

    def sync(self) -> SyncSummary:
        return self.sync_bidirectional()

    def sync_bidirectional(self) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        pull_summary = self._pull_with_spreadsheet(spreadsheet)
        # Garantiza persistencia local del pull antes de cualquier push/refresh de UI.
        self._connection.commit()
        push_summary = self._push_with_spreadsheet(spreadsheet)
        self._log_sync_stats("sync_bidirectional")
        return SyncSummary(
            inserted_local=pull_summary.inserted_local,
            updated_local=pull_summary.updated_local,
            inserted_remote=push_summary.inserted_remote,
            updated_remote=push_summary.updated_remote,
            duplicates_skipped=pull_summary.duplicates_skipped + push_summary.duplicates_skipped,
            conflicts_detected=pull_summary.conflicts_detected + push_summary.conflicts_detected,
            omitted_by_delegada=pull_summary.omitted_by_delegada + push_summary.omitted_by_delegada,
            errors=pull_summary.errors + push_summary.errors,
        )

    def simulate_sync_plan(self) -> SyncExecutionPlan:
        spreadsheet = self._ensure_connection_ready()
        return build_plan(self, spreadsheet)

    def execute_sync_plan(self, plan: SyncExecutionPlan) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        return execute_plan(self, spreadsheet, plan)

    def get_last_sync_at(self) -> str | None:
        return self._get_last_sync_at()

    def is_configured(self) -> bool:
        config = self._config_store.load()
        return bool(config and config.spreadsheet_id and config.credentials_path)

    def ensure_connection(self) -> None:
        self._ensure_connection_ready()

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
        rango = self._format_rango_fechas(fechas)
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

    def _pull_with_spreadsheet(self, spreadsheet: Any) -> SyncSummary:
        self._reset_write_batch_state()
        write_calls_before = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else 0
        last_sync_at = self._get_last_sync_at()
        downloaded = 0
        conflicts = 0
        omitted_duplicates = 0
        omitted_by_delegada = 0
        errors = 0
        solicitud_titles = self._solicitudes_pull_source_titles(spreadsheet)
        downloaded_count, conflict_count = self._pull_delegadas(spreadsheet, last_sync_at)
        downloaded += downloaded_count
        conflicts += conflict_count
        downloaded_count, conflict_count, duplicate_count, omitted_delegada_count, solicitud_errors = self._pull_solicitudes(
            spreadsheet, last_sync_at, solicitud_titles
        )
        downloaded += downloaded_count
        conflicts += conflict_count
        omitted_duplicates += duplicate_count
        omitted_by_delegada += omitted_delegada_count
        errors += solicitud_errors
        downloaded_count, conflict_count = self._pull_cuadrantes(spreadsheet, last_sync_at)
        downloaded += downloaded_count
        conflicts += conflict_count
        downloaded += self._pull_pdf_log(spreadsheet)
        downloaded += self._pull_config(spreadsheet)
        write_calls_after = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else 0
        logger.info("Write calls por sync (pull): %s", write_calls_after - write_calls_before)
        return SyncSummary(
            inserted_local=downloaded,
            updated_local=0,
            duplicates_skipped=omitted_duplicates,
            conflicts_detected=conflicts,
            omitted_by_delegada=omitted_by_delegada,
            errors=errors,
        )

    def _push_with_spreadsheet(self, spreadsheet: Any) -> SyncSummary:
        self._reset_write_batch_state()
        write_calls_before = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else 0
        last_sync_at = self._get_last_sync_at()
        uploaded = 0
        conflicts = 0
        omitted_duplicates = 0
        self._sync_local_cuadrantes_from_personas()
        uploaded_count, conflict_count = self._push_delegadas(spreadsheet, last_sync_at)
        uploaded += uploaded_count
        conflicts += conflict_count
        uploaded_count, conflict_count, duplicate_count = self._push_solicitudes(spreadsheet, last_sync_at)
        uploaded += uploaded_count
        conflicts += conflict_count
        omitted_duplicates += duplicate_count
        uploaded_count, conflict_count = self._push_cuadrantes(spreadsheet, last_sync_at)
        uploaded += uploaded_count
        conflicts += conflict_count
        uploaded += self._push_pdf_log(spreadsheet, last_sync_at)
        uploaded += self._push_config(spreadsheet, last_sync_at)
        self._set_last_sync_at(self._now_iso())
        write_calls_after = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else 0
        logger.info("Write calls por sync (push): %s", write_calls_after - write_calls_before)
        return SyncSummary(
            inserted_remote=uploaded,
            updated_remote=0,
            duplicates_skipped=omitted_duplicates,
            conflicts_detected=conflicts,
        )

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

    def _pull_delegadas(self, spreadsheet: Any, last_sync_at: str | None) -> tuple[int, int]:
        worksheet = self._get_worksheet(spreadsheet, "delegadas")
        headers, rows = self._rows_with_index(worksheet, "delegadas")
        downloaded = 0
        conflicts = 0
        for row_number, row in rows:
            nombre_value = str(row.get("nombre", "")).strip()
            uuid_value = str(row.get("uuid", "")).strip()
            if not uuid_value and not nombre_value:
                logger.warning("Fila delegada sin uuid ni nombre; se omite: %s", row)
                continue
            local_row, was_inserted, persona_uuid = self._get_or_create_persona(row)
            if self._enable_backfill and not str(row.get("uuid", "")).strip() and persona_uuid:
                self._backfill_uuid(worksheet, headers, row_number, "uuid", persona_uuid)
            if was_inserted:
                downloaded += 1
                continue
            if not uuid_value or local_row is None or local_row["uuid"] != uuid_value:
                # Sin UUID remoto, o con colisión de nombre+UUID, no hay clave remota estable para merge por timestamps.
                continue
            remote_updated_at = self._parse_iso(row.get("updated_at"))
            if self._is_conflict(local_row["updated_at"], remote_updated_at, last_sync_at):
                self._store_conflict("delegadas", uuid_value, dict(local_row), row)
                conflicts += 1
                continue
            if self._is_remote_newer(local_row["updated_at"], remote_updated_at):
                self._update_persona_from_remote(local_row["id"], row)
                downloaded += 1
        self._flush_write_batches(spreadsheet, worksheet)
        return downloaded, conflicts

    def _pull_solicitudes(
        self, spreadsheet: Any, last_sync_at: str | None, solicitud_titles: list[str] | None = None
    ) -> tuple[int, int, int, int, int]:
        stats = {"downloaded": 0, "conflicts": 0, "omitted_duplicates": 0, "omitted_by_delegada": 0, "errors": 0}
        for worksheet_name, worksheet in self._solicitudes_pull_sources(spreadsheet, solicitud_titles):
            worksheet_stats = self._pull_solicitudes_worksheet(worksheet_name, worksheet, last_sync_at)
            for key in stats:
                stats[key] += worksheet_stats[key]
            logger.info(
                "Pull solicitudes: worksheet=%s insertadas_local=%s actualizadas_local=%s",
                worksheet_name,
                worksheet_stats["inserted_ws"],
                worksheet_stats["updated_ws"],
            )
            logger.debug(
                "Pull solicitudes fechas: worksheet=%s ejemplo_antes='%s' ejemplo_despues='%s'",
                worksheet_name,
                worksheet_stats["sample_fecha_before"] or "",
                worksheet_stats["sample_fecha_after"] or "",
            )
            self._flush_write_batches(spreadsheet, worksheet)
        logger.info(
            "Pull solicitudes resumen: insertadas_local=%s omitidas_por_delegada=%s errores=%s",
            stats["downloaded"],
            stats["omitted_by_delegada"],
            stats["errors"],
        )
        return (
            stats["downloaded"],
            stats["conflicts"],
            stats["omitted_duplicates"],
            stats["omitted_by_delegada"],
            stats["errors"],
        )

    def _pull_solicitudes_worksheet(
        self, worksheet_name: str, worksheet: Any, last_sync_at: str | None
    ) -> dict[str, Any]:
        headers, rows = self._rows_with_index(
            worksheet,
            worksheet_name,
            aliases=self._solicitudes_header_aliases(),
        )
        stats: dict[str, Any] = {
            "downloaded": 0,
            "conflicts": 0,
            "omitted_duplicates": 0,
            "omitted_by_delegada": 0,
            "errors": 0,
            "inserted_ws": 0,
            "updated_ws": 0,
            "sample_fecha_before": None,
            "sample_fecha_after": None,
        }
        logger.info("Pull solicitudes: worksheet=%s filas_leidas=%s", worksheet_name, len(rows))
        for row_number, raw_row in rows:
            self._set_pull_solicitud_samples(stats, raw_row)
            row = self._normalize_remote_solicitud_row(raw_row, worksheet_name)
            if stats["sample_fecha_after"] is None:
                stats["sample_fecha_after"] = str(row.get("fecha") or "")
            self._process_pull_solicitud_row(worksheet, headers, row_number, row, last_sync_at, stats)
        return stats

    @staticmethod
    def _set_pull_solicitud_samples(stats: dict[str, Any], raw_row: dict[str, Any]) -> None:
        if stats["sample_fecha_before"] is None:
            stats["sample_fecha_before"] = str(raw_row.get("fecha") or raw_row.get("fecha_pedida") or "")

    def _process_pull_solicitud_row(
        self,
        worksheet: Any,
        headers: list[str],
        row_number: int,
        row: dict[str, Any],
        last_sync_at: str | None,
        stats: dict[str, Any],
    ) -> None:
        uuid_value = str(row.get("uuid", "")).strip()
        if not uuid_value:
            self._handle_pull_solicitud_without_uuid(worksheet, headers, row_number, row, stats)
            return
        self._handle_pull_solicitud_with_uuid(uuid_value, row, last_sync_at, stats)

    def _handle_pull_solicitud_without_uuid(
        self, worksheet: Any, headers: list[str], row_number: int, row: dict[str, Any], stats: dict[str, Any]
    ) -> None:
        existing = self._find_solicitud_by_composite_key(row)
        if existing is not None:
            stats["omitted_duplicates"] += 1
            uuid_value = str(existing["uuid"] or "").strip()
        else:
            uuid_value = self._generate_uuid()
            self._accumulate_write_result(
                stats,
                self._insert_solicitud_from_remote(uuid_value, row),
                "inserted_ws",
            )
        if self._enable_backfill:
            self._backfill_uuid(worksheet, headers, row_number, "uuid", uuid_value)

    def _handle_pull_solicitud_with_uuid(
        self, uuid_value: str, row: dict[str, Any], last_sync_at: str | None, stats: dict[str, Any]
    ) -> None:
        remote_updated_at = self._parse_iso(row.get("updated_at"))
        local_row = self._fetch_solicitud(uuid_value)
        if local_row is None:
            if self._skip_pull_duplicate(uuid_value, row, stats):
                return
            self._accumulate_write_result(
                stats,
                self._insert_solicitud_from_remote(uuid_value, row),
                "inserted_ws",
            )
            return
        if self._is_conflict(local_row["updated_at"], remote_updated_at, last_sync_at):
            self._store_conflict("solicitudes", uuid_value, dict(local_row), row)
            stats["conflicts"] += 1
            return
        if self._is_remote_newer(local_row["updated_at"], remote_updated_at):
            self._accumulate_write_result(
                stats,
                self._update_solicitud_from_remote(local_row["id"], row),
                "updated_ws",
            )

    def _skip_pull_duplicate(self, uuid_value: str, row: dict[str, Any], stats: dict[str, Any]) -> bool:
        duplicate_key = self._solicitud_dedupe_key_from_remote_row(row)
        if not duplicate_key or not self._is_duplicate_local_solicitud(duplicate_key, exclude_uuid=uuid_value):
            return False
        logger.info(
            "Omitiendo solicitud duplicada en pull. clave=%s registro=%s",
            duplicate_key,
            row,
        )
        stats["omitted_duplicates"] += 1
        return True

    @staticmethod
    def _accumulate_write_result(stats: dict[str, Any], result: tuple[bool, int, int], operation_counter: str) -> None:
        written, omitted_delegada, operation_errors = result
        stats["downloaded"] += 1 if written else 0
        stats[operation_counter] += 1 if written else 0
        stats["omitted_by_delegada"] += omitted_delegada
        stats["errors"] += operation_errors

    @staticmethod
    def _solicitudes_header_aliases() -> dict[str, list[str]]:
        return {
            "uuid": ["id", "solicitud_uuid"],
            "delegada_uuid": ["delegado_uuid", "persona_uuid"],
            "delegada_nombre": ["Delegada", "delegado_nombre", "delegada", "delegado", "persona_nombre", "nombre"],
            "fecha": ["fecha_pedida", "dia", "fecha solicitud"],
            "desde": ["desde_hora", "hora_desde"],
            "hasta": ["hasta_hora", "hora_hasta"],
            "completo": ["es_completo", "jornada_completa"],
            "horas": ["minutos_total", "horas_solicitadas", "total_minutos"],
            "notas": ["observaciones", "comentarios"],
        }

    def _solicitudes_pull_source_titles(self, spreadsheet: Any) -> list[str]:
        worksheets_by_title = self._client.get_worksheets_by_title()
        self._worksheet_cache.update(worksheets_by_title)
        titles: list[str] = []
        for name in ("solicitudes", "Histórico", "Historico"):
            if name in worksheets_by_title and name not in titles:
                titles.append(name)
        if not titles:
            raise SheetsConfigError("No existe worksheet 'solicitudes' ni 'Histórico' en el Spreadsheet.")
        return titles

    def _solicitudes_pull_sources(
        self, spreadsheet: Any, titles: list[str] | None = None
    ) -> list[tuple[str, Any]]:
        selected_titles = titles or self._solicitudes_pull_source_titles(spreadsheet)
        return [(title, self._get_worksheet(spreadsheet, title)) for title in selected_titles]


    def _normalize_remote_solicitud_row(self, row: dict[str, Any], worksheet_name: str) -> dict[str, Any]:
        return sync_sheets_core.normalize_remote_solicitud_row(row, worksheet_name)

    @staticmethod
    def _remote_hhmm(hours: Any, minutes: Any, full_value: Any) -> str | None:
        return sync_sheets_core.remote_hhmm(hours, minutes, full_value)

    def _pull_cuadrantes(
        self, spreadsheet: Any, last_sync_at: str | None
    ) -> tuple[int, int]:
        worksheet = self._get_worksheet(spreadsheet, "cuadrantes")
        _, rows = self._rows_with_index(worksheet)
        downloaded = 0
        conflicts = 0
        for _, row in rows:
            uuid_value = str(row.get("uuid", "")).strip()
            if not uuid_value:
                continue
            remote_updated_at = self._parse_iso(row.get("updated_at"))
            local_row = self._fetch_cuadrante(uuid_value)
            if local_row is None:
                self._insert_cuadrante_from_remote(uuid_value, row)
                downloaded += 1
                continue
            if self._is_conflict(local_row["updated_at"], remote_updated_at, last_sync_at):
                self._store_conflict("cuadrantes", uuid_value, dict(local_row), row)
                conflicts += 1
                continue
            if self._is_remote_newer(local_row["updated_at"], remote_updated_at):
                self._update_cuadrante_from_remote(local_row["id"], row)
                downloaded += 1
        return downloaded, conflicts

    def _pull_pdf_log(self, spreadsheet: Any) -> int:
        worksheet = self._get_worksheet(spreadsheet, "pdf_log")
        _, rows = self._rows_with_index(worksheet)
        downloaded = 0
        cursor = self._connection.cursor()
        for _, row in rows:
            pdf_id = str(row.get("pdf_id", "")).strip()
            if not pdf_id:
                continue
            cursor.execute(
                "SELECT updated_at FROM pdf_log WHERE pdf_id = ?",
                (pdf_id,),
            )
            existing = cursor.fetchone()
            if existing is None:
                cursor.execute(
                    """
                    INSERT INTO pdf_log (pdf_id, delegada_uuid, rango_fechas, fecha_generacion, hash, updated_at, source_device)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pdf_id,
                        row.get("delegada_uuid"),
                        row.get("rango_fechas"),
                        row.get("fecha_generacion"),
                        row.get("hash"),
                        row.get("updated_at"),
                        row.get("source_device"),
                    ),
                )
                downloaded += 1
            elif self._is_remote_newer(existing["updated_at"], self._parse_iso(row.get("updated_at"))):
                cursor.execute(
                    """
                    UPDATE pdf_log
                    SET delegada_uuid = ?, rango_fechas = ?, fecha_generacion = ?, hash = ?, updated_at = ?, source_device = ?
                    WHERE pdf_id = ?
                    """,
                    (
                        row.get("delegada_uuid"),
                        row.get("rango_fechas"),
                        row.get("fecha_generacion"),
                        row.get("hash"),
                        row.get("updated_at"),
                        row.get("source_device"),
                        pdf_id,
                    ),
                )
                downloaded += 1
        self._connection.commit()
        return downloaded

    def _pull_config(self, spreadsheet: Any) -> int:
        worksheet = self._get_worksheet(spreadsheet, "config")
        _, rows = self._rows_with_index(worksheet)
        downloaded = 0
        cursor = self._connection.cursor()
        for _, row in rows:
            key = str(row.get("key", "")).strip()
            if not key:
                continue
            cursor.execute("SELECT updated_at FROM sync_config WHERE key = ?", (key,))
            existing = cursor.fetchone()
            if existing is None:
                cursor.execute(
                    """
                    INSERT INTO sync_config (key, value, updated_at, source_device)
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, row.get("value"), row.get("updated_at"), row.get("source_device")),
                )
                downloaded += 1
                self._apply_config_value(key, row.get("value"))
            elif self._is_remote_newer(existing["updated_at"], self._parse_iso(row.get("updated_at"))):
                cursor.execute(
                    """
                    UPDATE sync_config
                    SET value = ?, updated_at = ?, source_device = ?
                    WHERE key = ?
                    """,
                    (row.get("value"), row.get("updated_at"), row.get("source_device"), key),
                )
                downloaded += 1
                self._apply_config_value(key, row.get("value"))
        self._connection.commit()
        return downloaded

    def _push_pdf_log(self, spreadsheet: Any, last_sync_at: str | None) -> int:
        worksheet = self._get_worksheet(spreadsheet, "pdf_log")
        headers, rows = self._rows_with_index(worksheet)
        header_map = self._header_map(headers, SHEETS_SCHEMA["pdf_log"])
        remote_index = {row["pdf_id"]: row for _, row in rows if row.get("pdf_id")}
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT pdf_id, delegada_uuid, rango_fechas, fecha_generacion, hash, updated_at, source_device
            FROM pdf_log
            WHERE updated_at IS NOT NULL
            """
        )
        uploaded = 0
        for row in cursor.fetchall():
            if not self._is_after_last_sync(row["updated_at"], last_sync_at):
                continue
            remote_row = remote_index.get(row["pdf_id"])
            remote_updated_at = self._parse_iso(remote_row.get("updated_at") if remote_row else None)
            local_updated_at = self._parse_iso(row["updated_at"])
            if remote_row and remote_updated_at and local_updated_at and remote_updated_at > local_updated_at:
                continue
            payload = {
                "pdf_id": row["pdf_id"],
                "delegada_uuid": row["delegada_uuid"],
                "rango_fechas": row["rango_fechas"],
                "fecha_generacion": row["fecha_generacion"],
                "hash": row["hash"],
                "updated_at": row["updated_at"],
                "source_device": row["source_device"] or self._device_id(),
            }
            if remote_row:
                if self._enable_backfill:
                    row_number = remote_row["__row_number__"]
                    self._update_row(worksheet, row_number, header_map, payload)
                continue
            self._append_row(worksheet, header_map, payload)
            uploaded += 1
        self._flush_write_batches(spreadsheet, worksheet)
        return uploaded

    def _push_config(self, spreadsheet: Any, last_sync_at: str | None) -> int:
        worksheet = self._get_worksheet(spreadsheet, "config")
        headers, rows = self._rows_with_index(worksheet)
        header_map = self._header_map(headers, SHEETS_SCHEMA["config"])
        remote_index = {row["key"]: row for _, row in rows if row.get("key")}
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT key, value, updated_at, source_device
            FROM sync_config
            WHERE updated_at IS NOT NULL
            """
        )
        uploaded = 0
        for row in cursor.fetchall():
            if not self._is_after_last_sync(row["updated_at"], last_sync_at):
                continue
            remote_row = remote_index.get(row["key"])
            remote_updated_at = self._parse_iso(remote_row.get("updated_at") if remote_row else None)
            local_updated_at = self._parse_iso(row["updated_at"])
            if remote_row and remote_updated_at and local_updated_at and remote_updated_at > local_updated_at:
                continue
            payload = {
                "key": row["key"],
                "value": row["value"],
                "updated_at": row["updated_at"],
                "source_device": row["source_device"] or self._device_id(),
            }
            if remote_row:
                if self._enable_backfill:
                    row_number = remote_row["__row_number__"]
                    self._update_row(worksheet, row_number, header_map, payload)
                continue
            self._append_row(worksheet, header_map, payload)
            uploaded += 1
        self._flush_write_batches(spreadsheet, worksheet)
        return uploaded

    def _push_delegadas(
        self, spreadsheet: Any, last_sync_at: str | None
    ) -> tuple[int, int]:
        worksheet = self._get_worksheet(spreadsheet, "delegadas")
        headers, rows = self._rows_with_index(worksheet)
        header_map = self._header_map(headers, SHEETS_SCHEMA["delegadas"])
        remote_index = self._uuid_index(rows)
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min,
                   updated_at, source_device, deleted
            FROM personas
            WHERE updated_at IS NOT NULL
            """
        )
        uploaded = 0
        conflicts = 0
        for row in cursor.fetchall():
            if not self._is_after_last_sync(row["updated_at"], last_sync_at):
                continue
            uuid_value = row["uuid"]
            remote_row = remote_index.get(uuid_value)
            remote_updated_at = self._parse_iso(remote_row.get("updated_at") if remote_row else None)
            if self._is_conflict(row["updated_at"], remote_updated_at, last_sync_at):
                self._store_conflict("delegadas", uuid_value, dict(row), remote_row or {})
                conflicts += 1
                continue
            payload = {
                "uuid": uuid_value,
                "nombre": row["nombre"],
                "genero": row["genero"],
                "activa": 1 if row["is_active"] else 0,
                "bolsa_mes_min": row["horas_mes_min"] or 0,
                "bolsa_anual_min": row["horas_ano_min"] or 0,
                "updated_at": row["updated_at"],
                "source_device": row["source_device"] or self._device_id(),
                "deleted": row["deleted"] or 0,
            }
            if remote_row:
                if self._enable_backfill:
                    row_number = remote_row["__row_number__"]
                    self._update_row(worksheet, row_number, header_map, payload)
                continue
            self._append_row(worksheet, header_map, payload)
            uploaded += 1
        self._flush_write_batches(spreadsheet, worksheet)
        return uploaded, conflicts

    def _push_solicitudes(
        self, spreadsheet: Any, last_sync_at: str | None
    ) -> tuple[int, int, int]:
        worksheet = self._get_worksheet(spreadsheet, "solicitudes")
        headers, rows = self._rows_with_index(worksheet)
        remote_index = self._uuid_index(rows)
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT s.id, s.uuid, s.persona_id, s.fecha_pedida, s.desde_min, s.hasta_min,
                   s.completo, s.horas_solicitadas_min, s.notas, s.created_at, s.updated_at,
                   s.source_device, s.deleted, s.pdf_hash,
                   p.uuid AS delegada_uuid, p.nombre AS delegada_nombre
            FROM solicitudes s
            JOIN personas p ON p.id = s.persona_id
            WHERE s.updated_at IS NOT NULL
            """
        )
        uploaded = 0
        conflicts = 0
        omitted_duplicates = 0
        values: list[list[Any]] = [HEADER_CANONICO_SOLICITUDES]
        local_uuids: set[str] = set()
        for row in cursor.fetchall():
            should_upload, row_conflict = self._push_solicitud_local_row(
                row,
                remote_index,
                last_sync_at,
                values,
                local_uuids,
            )
            uploaded += 1 if should_upload else 0
            conflicts += 1 if row_conflict else 0

        for _, remote_row in rows:
            if self._append_push_solicitud_remote_only_row(remote_row, local_uuids, values):
                omitted_duplicates += 1

        if headers != HEADER_CANONICO_SOLICITUDES:
            logger.info("Reescribiendo encabezado canónico de 'solicitudes' (sin columnas extras o vacías).")
            self._normalize_solicitudes_header(worksheet)

        worksheet.update("A1", values)
        logger.info("PUSH Sheets: %s filas enviadas", max(len(values) - 1, 0))
        return uploaded, conflicts, omitted_duplicates

    def _push_solicitud_local_row(
        self,
        row: Any,
        remote_index: dict[str, dict[str, Any]],
        last_sync_at: str | None,
        values: list[list[Any]],
        local_uuids: set[str],
    ) -> tuple[bool, bool]:
        if last_sync_at and not self._is_after_last_sync(row["updated_at"], last_sync_at):
            return False, False
        uuid_value = row["uuid"]
        local_uuids.add(uuid_value)
        remote_row = remote_index.get(uuid_value)
        remote_updated_at = self._parse_iso(remote_row.get("updated_at") if remote_row else None)
        if self._is_conflict(row["updated_at"], remote_updated_at, last_sync_at):
            self._store_conflict("solicitudes", uuid_value, dict(row), remote_row or {})
            return False, True
        values.append(list(self._local_solicitud_payload(row)))
        return True, False

    def _append_push_solicitud_remote_only_row(
        self, remote_row: dict[str, Any], local_uuids: set[str], values: list[list[Any]]
    ) -> bool:
        remote_uuid = str(remote_row.get("uuid", "")).strip()
        if not remote_uuid or remote_uuid in local_uuids:
            return False
        values.append(list(self._remote_solicitud_payload(remote_row)))
        return True

    def _build_solicitudes_sync_plan(self, spreadsheet: Any) -> SyncExecutionPlan:
        return build_solicitudes_sync_plan(self, spreadsheet, HEADER_CANONICO_SOLICITUDES)

    def _local_solicitud_payload(self, row: Any) -> tuple[Any, ...]:
        return (
            row["uuid"],
            row["delegada_uuid"] or "",
            row["delegada_nombre"] or "",
            self._to_iso_date(row["fecha_pedida"]),
            self._hour_component(row["desde_min"]),
            self._minute_component(row["desde_min"]),
            self._hour_component(row["hasta_min"]),
            self._minute_component(row["hasta_min"]),
            1 if row["completo"] else 0,
            self._int_or_zero(row["horas_solicitadas_min"]),
            row["notas"] or "",
            "",
            self._to_iso_date(row["created_at"]),
            self._to_iso_date(row["updated_at"]),
            row["source_device"] or self._device_id(),
            self._int_or_zero(row["deleted"]),
            row["pdf_hash"] or "",
        )

    def _remote_solicitud_payload(self, remote_row: dict[str, Any]) -> tuple[Any, ...]:
        desde_hhmm = remote_row.get("desde") or self._remote_hhmm(
            remote_row.get("desde_h"), remote_row.get("desde_m"), None
        )
        hasta_hhmm = remote_row.get("hasta") or self._remote_hhmm(
            remote_row.get("hasta_h"), remote_row.get("hasta_m"), None
        )
        return (
            remote_row.get("uuid", ""),
            remote_row.get("delegada_uuid") or remote_row.get("delegado_uuid") or "",
            remote_row.get("delegada_nombre") or remote_row.get("Delegada") or remote_row.get("delegado_nombre") or "",
            self._to_iso_date(remote_row.get("fecha") or remote_row.get("fecha_pedida")),
            self._hour_component_from_hhmm(desde_hhmm),
            self._minute_component_from_hhmm(desde_hhmm),
            self._hour_component_from_hhmm(hasta_hhmm),
            self._minute_component_from_hhmm(hasta_hhmm),
            self._int_or_zero(remote_row.get("completo")),
            self._int_or_zero(remote_row.get("horas") or remote_row.get("minutos_total")),
            remote_row.get("notas") or "",
            remote_row.get("estado") or "",
            self._to_iso_date(remote_row.get("created_at") or remote_row.get("fecha")),
            self._to_iso_date(remote_row.get("updated_at")),
            remote_row.get("source_device") or "",
            self._int_or_zero(remote_row.get("deleted")),
            remote_row.get("pdf_id") or "",
        )

    def _push_cuadrantes(
        self, spreadsheet: Any, last_sync_at: str | None
    ) -> tuple[int, int]:
        worksheet = self._get_worksheet(spreadsheet, "cuadrantes")
        headers, rows = self._rows_with_index(worksheet)
        header_map = self._header_map(headers, SHEETS_SCHEMA["cuadrantes"])
        remote_index = self._uuid_index(rows)
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, source_device, deleted
            FROM cuadrantes
            WHERE updated_at IS NOT NULL
            """
        )
        uploaded = 0
        conflicts = 0
        for row in cursor.fetchall():
            if not self._is_after_last_sync(row["updated_at"], last_sync_at):
                continue
            uuid_value = row["uuid"]
            remote_row = remote_index.get(uuid_value)
            remote_updated_at = self._parse_iso(remote_row.get("updated_at") if remote_row else None)
            if self._is_conflict(row["updated_at"], remote_updated_at, last_sync_at):
                self._store_conflict("cuadrantes", uuid_value, dict(row), remote_row or {})
                conflicts += 1
                continue
            man_h, man_m = self._split_minutes(row["man_min"])
            tar_h, tar_m = self._split_minutes(row["tar_min"])
            payload = {
                "uuid": uuid_value,
                "delegada_uuid": row["delegada_uuid"],
                "dia_semana": row["dia_semana"],
                "man_h": man_h,
                "man_m": man_m,
                "tar_h": tar_h,
                "tar_m": tar_m,
                "updated_at": row["updated_at"],
                "source_device": row["source_device"] or self._device_id(),
                "deleted": row["deleted"] or 0,
            }
            if remote_row:
                if self._enable_backfill:
                    row_number = remote_row["__row_number__"]
                    self._update_row(worksheet, row_number, header_map, payload)
                continue
            self._append_row(worksheet, header_map, payload)
            uploaded += 1
        self._flush_write_batches(spreadsheet, worksheet)
        return uploaded, conflicts

    def _fetch_persona(self, uuid_value: str) -> Any | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min,
                   updated_at, source_device, deleted,
                   cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                   cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                   cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                   cuad_dom_man_min, cuad_dom_tar_min
            FROM personas
            WHERE uuid = ?
            """,
            (uuid_value,),
        )
        return cursor.fetchone()

    def _fetch_persona_by_nombre(self, nombre: str) -> Any | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min,
                   updated_at, source_device, deleted,
                   cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                   cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                   cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                   cuad_dom_man_min, cuad_dom_tar_min
            FROM personas
            WHERE nombre = ?
            """,
            (nombre,),
        )
        return cursor.fetchone()

    def _get_or_create_persona(self, row: dict[str, Any]) -> tuple[Any | None, bool, str | None]:
        persona_uuid = str(row.get("uuid", "")).strip() or None
        nombre = str(row.get("nombre", "")).strip()

        if persona_uuid:
            by_uuid = self._fetch_persona(persona_uuid)
            if by_uuid is not None:
                logger.info("Persona existente: uuid=%s, nombre=%s", by_uuid["uuid"], by_uuid["nombre"])
                return by_uuid, False, by_uuid["uuid"]

            by_nombre = self._fetch_persona_by_nombre(nombre) if nombre else None
            if by_nombre is not None:
                existing_uuid = (by_nombre["uuid"] or "").strip()
                if existing_uuid and existing_uuid != persona_uuid:
                    logger.warning(
                        "Colisión persona por nombre; se prioriza existente. nombre=%s uuid_local=%s uuid_remoto=%s",
                        nombre,
                        existing_uuid,
                        persona_uuid,
                    )
                elif not existing_uuid:
                    cursor = self._connection.cursor()
                    cursor.execute(
                        "UPDATE personas SET uuid = ?, updated_at = ? WHERE id = ?",
                        (persona_uuid, row.get("updated_at") or self._now_iso(), by_nombre["id"]),
                    )
                    self._connection.commit()
                    by_nombre = self._fetch_persona(persona_uuid) or by_nombre
                logger.info("Persona existente: uuid=%s, nombre=%s", by_nombre["uuid"], by_nombre["nombre"])
                return by_nombre, False, by_nombre["uuid"]

            logger.info("Insertando persona nueva: uuid=%s, nombre=%s", persona_uuid, nombre)
            self._insert_persona_from_remote(persona_uuid, row)
            return self._fetch_persona(persona_uuid), True, persona_uuid

        by_nombre = self._fetch_persona_by_nombre(nombre) if nombre else None
        if by_nombre is not None:
            logger.info("Persona existente: uuid=%s, nombre=%s", by_nombre["uuid"], by_nombre["nombre"])
            return by_nombre, False, by_nombre["uuid"]

        generated_uuid = self._generate_uuid()
        logger.info("Insertando persona nueva: uuid=%s, nombre=%s", generated_uuid, nombre)
        self._insert_persona_from_remote(generated_uuid, row)
        return self._fetch_persona(generated_uuid), True, generated_uuid

    def _find_solicitud_by_composite_key(self, row: dict[str, Any]) -> Any | None:
        delegada_uuid = str(row.get("delegada_uuid", "")).strip() or None
        fecha = self._normalize_date(row.get("fecha"))
        completo = bool(self._int_or_zero(row.get("completo")))
        desde = normalize_hhmm(f"{self._int_or_zero(row.get('desde_h')):02d}:{self._int_or_zero(row.get('desde_m')):02d}")
        hasta = normalize_hhmm(f"{self._int_or_zero(row.get('hasta_h')):02d}:{self._int_or_zero(row.get('hasta_m')):02d}")
        key = solicitud_unique_key(delegada_uuid, fecha, completo, desde, hasta)
        if key is None:
            return None
        persona_id = self._persona_id_from_uuid(delegada_uuid)
        if persona_id is None:
            return None
        cursor = self._connection.cursor()
        desde_min = self._parse_hhmm_to_minutes(desde)
        hasta_min = self._parse_hhmm_to_minutes(hasta)
        cursor.execute(
            """
            SELECT id, uuid, persona_id, fecha_pedida, desde_min, hasta_min, completo,
                   horas_solicitadas_min, notas, created_at, updated_at, source_device, deleted, pdf_hash
            FROM solicitudes
            WHERE persona_id = ? AND fecha_pedida = ? AND completo = ?
              AND (desde_min IS ? OR desde_min = ?) AND (hasta_min IS ? OR hasta_min = ?)
              AND (deleted = 0 OR deleted IS NULL)
            LIMIT 1
            """,
            (persona_id, key[1], 1 if key[2] else 0, desde_min, desde_min, hasta_min, hasta_min),
        )
        return cursor.fetchone()

    def _backfill_uuid(self, worksheet: Any, headers: list[str], row_number: int, column: str, value: str) -> None:
        if not self._enable_backfill or not value:
            return
        if column not in headers:
            return
        col_idx = headers.index(column) + 1
        # Evita write-per-row: acumulamos backfills y se ejecutan en un único values_batch_update por worksheet.
        self._queue_values_batch_update(worksheet, row_number, col_idx, value)

    def _fetch_solicitud(self, uuid_value: str) -> Any | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, uuid, persona_id, fecha_pedida, desde_min, hasta_min, completo,
                   horas_solicitadas_min, notas, created_at, updated_at, source_device, deleted, pdf_hash
            FROM solicitudes
            WHERE uuid = ?
            """,
            (uuid_value,),
        )
        return cursor.fetchone()

    def _fetch_cuadrante(self, uuid_value: str) -> Any | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, source_device, deleted
            FROM cuadrantes
            WHERE uuid = ?
            """,
            (uuid_value,),
        )
        return cursor.fetchone()

    def _insert_persona_from_remote(self, uuid_value: str, row: dict[str, Any]) -> None:
        cursor = self._connection.cursor()
        execute_with_validation(
            cursor,
            """
            INSERT INTO personas (
                uuid, nombre, genero, horas_mes_min, horas_ano_min, horas_jornada_defecto_min, is_active,
                cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                cuad_dom_man_min, cuad_dom_tar_min,
                updated_at, source_device, deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid_value,
                row.get("nombre"),
                row.get("genero"),
                self._int_or_zero(row.get("bolsa_mes_min")),
                self._int_or_zero(row.get("bolsa_anual_min")),
                0,
                1 if self._int_or_zero(row.get("activa")) else 0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                row.get("updated_at") or self._now_iso(),
                row.get("source_device"),
                self._int_or_zero(row.get("deleted")),
            ),
            "personas.insert_remote",
        )
        self._connection.commit()

    def _update_persona_from_remote(self, persona_id: int, row: dict[str, Any]) -> None:
        cursor = self._connection.cursor()
        deleted = self._int_or_zero(row.get("deleted"))
        execute_with_validation(
            cursor,
            """
            UPDATE personas
            SET nombre = ?, genero = ?, horas_mes_min = ?, horas_ano_min = ?, is_active = ?,
                updated_at = ?, source_device = ?, deleted = ?
            WHERE id = ?
            """,
            (
                row.get("nombre"),
                row.get("genero"),
                self._int_or_zero(row.get("bolsa_mes_min")),
                self._int_or_zero(row.get("bolsa_anual_min")),
                0 if deleted else (1 if self._int_or_zero(row.get("activa")) else 0),
                row.get("updated_at") or self._now_iso(),
                row.get("source_device"),
                deleted,
                persona_id,
            ),
            "personas.update_remote",
        )
        self._connection.commit()

    def _insert_solicitud_from_remote(self, uuid_value: str, row: dict[str, Any]) -> tuple[bool, int, int]:
        cursor = self._connection.cursor()
        delegada_uuid = str(row.get("delegada_uuid") or "").strip()
        delegada_nombre = " ".join(str(row.get("delegada_nombre") or row.get("Delegada") or "").split())
        if not delegada_uuid:
            logger.warning(
                "Solicitud %s sin delegada_uuid, resolviendo por nombre '%s'",
                uuid_value,
                delegada_nombre,
            )
        resolved_uuid = get_or_resolve_delegada_uuid(self._connection, delegada_uuid, delegada_nombre)
        if not resolved_uuid:
            logger.warning("Solicitud omitida por delegada no resuelta: %s", uuid_value)
            return False, 1, 1
        persona_id = self._persona_id_from_uuid(resolved_uuid)
        if persona_id is None:
            logger.warning("Solicitud omitida por delegada no resuelta: %s", uuid_value)
            return False, 1, 1
        logger.info("Delegada resuelta: %s %s", resolved_uuid, delegada_nombre)
        fecha_normalizada = self._normalize_date(row.get("fecha") or row.get("fecha_pedida"))
        created_normalizada = self._normalize_date(row.get("created_at")) or fecha_normalizada
        if not fecha_normalizada:
            logger.warning("Solicitud %s descartada por fecha inválida en pull: %s", uuid_value, row.get("fecha"))
            return False, 0, 1
        desde_min = self._join_minutes(row.get("desde_h"), row.get("desde_m"))
        hasta_min = self._join_minutes(row.get("hasta_h"), row.get("hasta_m"))
        execute_with_validation(
            cursor,
            """
            INSERT INTO solicitudes (
                uuid, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash,
                generated, created_at, updated_at, source_device, deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid_value,
                persona_id,
                created_normalizada,
                fecha_normalizada,
                desde_min,
                hasta_min,
                1 if self._int_or_zero(row.get("completo")) else 0,
                self._int_or_zero(row.get("minutos_total") or row.get("horas")),
                None,
                row.get("notas") or "",
                None,
                row.get("pdf_id"),
                1,
                created_normalizada,
                row.get("updated_at") or self._now_iso(),
                row.get("source_device"),
                self._int_or_zero(row.get("deleted")),
            ),
            "solicitudes.insert_remote",
        )
        self._connection.commit()
        logger.info("Solicitud importada a tabla local 'solicitudes' (histórico): uuid=%s", uuid_value)
        return True, 0, 0

    def _update_solicitud_from_remote(self, solicitud_id: int, row: dict[str, Any]) -> tuple[bool, int, int]:
        cursor = self._connection.cursor()
        delegada_uuid = str(row.get("delegada_uuid") or "").strip()
        delegada_nombre = " ".join(str(row.get("delegada_nombre") or row.get("Delegada") or "").split())
        if not delegada_uuid:
            logger.warning(
                "Solicitud %s sin delegada_uuid, resolviendo por nombre '%s'",
                row.get("uuid") or solicitud_id,
                delegada_nombre,
            )
        resolved_uuid = get_or_resolve_delegada_uuid(self._connection, delegada_uuid, delegada_nombre)
        if not resolved_uuid:
            logger.warning("Solicitud omitida por delegada no resuelta: %s", row.get("uuid") or solicitud_id)
            return False, 1, 1
        persona_id = self._persona_id_from_uuid(resolved_uuid)
        if persona_id is None:
            logger.warning("Solicitud omitida por delegada no resuelta: %s", row.get("uuid") or solicitud_id)
            return False, 1, 1
        logger.info("Delegada resuelta: %s %s", resolved_uuid, delegada_nombre)
        fecha_normalizada = self._normalize_date(row.get("fecha") or row.get("fecha_pedida"))
        created_normalizada = self._normalize_date(row.get("created_at")) or fecha_normalizada
        if not fecha_normalizada:
            logger.warning("Solicitud id=%s no actualizada por fecha inválida en pull: %s", solicitud_id, row.get("fecha"))
            return False, 0, 1
        desde_min = self._join_minutes(row.get("desde_h"), row.get("desde_m"))
        hasta_min = self._join_minutes(row.get("hasta_h"), row.get("hasta_m"))
        execute_with_validation(
            cursor,
            """
            UPDATE solicitudes
            SET persona_id = ?, fecha_pedida = ?, desde_min = ?, hasta_min = ?, completo = ?,
                horas_solicitadas_min = ?, notas = ?, pdf_hash = ?, created_at = ?, updated_at = ?,
                source_device = ?, deleted = ?, generated = 1
            WHERE id = ?
            """,
            (
                persona_id,
                fecha_normalizada,
                desde_min,
                hasta_min,
                1 if self._int_or_zero(row.get("completo")) else 0,
                self._int_or_zero(row.get("minutos_total") or row.get("horas")),
                row.get("notas") or "",
                row.get("pdf_id"),
                created_normalizada,
                row.get("updated_at") or self._now_iso(),
                row.get("source_device"),
                self._int_or_zero(row.get("deleted")),
                solicitud_id,
            ),
            "solicitudes.update_remote",
        )
        self._connection.commit()
        return True, 0, 0

    @staticmethod
    def _normalize_date(value: str | None) -> str | None:
        return sync_sheets_core.normalize_date(value)

    @staticmethod
    def _to_iso_date(value: Any) -> str:
        return sync_sheets_core.to_iso_date(value)

    def _minutes_to_hhmm(self, value: Any) -> str:
        hours, minutes = self._split_minutes(value)
        return f"{hours:02d}:{minutes:02d}"

    def _hour_component(self, value: Any) -> int:
        hours, _ = self._split_minutes(value)
        return hours

    def _minute_component(self, value: Any) -> int:
        _, minutes = self._split_minutes(value)
        return minutes

    def _hour_component_from_hhmm(self, value: Any) -> int | str:
        normalized = normalize_hhmm(str(value).strip()) if value not in (None, "") else None
        if not normalized:
            return ""
        return int(normalized.split(":")[0])

    def _minute_component_from_hhmm(self, value: Any) -> int | str:
        normalized = normalize_hhmm(str(value).strip()) if value not in (None, "") else None
        if not normalized:
            return ""
        return int(normalized.split(":")[1])

    def _normalize_solicitudes_header(self, worksheet: Any) -> None:
        worksheet.update("A1", [HEADER_CANONICO_SOLICITUDES])
        try:
            worksheet.resize(cols=len(HEADER_CANONICO_SOLICITUDES))
        except OSError:
            logger.debug("No se pudo ajustar columnas de la worksheet 'solicitudes'.", exc_info=True)

    def _insert_cuadrante_from_remote(self, uuid_value: str, row: dict[str, Any]) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO cuadrantes (
                uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, source_device, deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid_value,
                row.get("delegada_uuid"),
                row.get("dia_semana"),
                self._join_minutes(row.get("man_h"), row.get("man_m")),
                self._join_minutes(row.get("tar_h"), row.get("tar_m")),
                row.get("updated_at") or self._now_iso(),
                row.get("source_device"),
                self._int_or_zero(row.get("deleted")),
            ),
        )
        self._connection.commit()
        self._apply_cuadrante_to_persona(row)

    def _update_cuadrante_from_remote(self, cuadrante_id: int, row: dict[str, Any]) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            UPDATE cuadrantes
            SET delegada_uuid = ?, dia_semana = ?, man_min = ?, tar_min = ?, updated_at = ?, source_device = ?, deleted = ?
            WHERE id = ?
            """,
            (
                row.get("delegada_uuid"),
                row.get("dia_semana"),
                self._join_minutes(row.get("man_h"), row.get("man_m")),
                self._join_minutes(row.get("tar_h"), row.get("tar_m")),
                row.get("updated_at") or self._now_iso(),
                row.get("source_device"),
                self._int_or_zero(row.get("deleted")),
                cuadrante_id,
            ),
        )
        self._connection.commit()
        self._apply_cuadrante_to_persona(row)

    def _apply_cuadrante_to_persona(self, row: dict[str, Any]) -> None:
        delegada_uuid = row.get("delegada_uuid")
        dia = self._normalize_dia(str(row.get("dia_semana", "")))
        if not delegada_uuid or not dia:
            return
        persona_id = self._persona_id_from_uuid(delegada_uuid)
        if persona_id is None:
            return
        man_min = self._join_minutes(row.get("man_h"), row.get("man_m"))
        tar_min = self._join_minutes(row.get("tar_h"), row.get("tar_m"))
        cursor = self._connection.cursor()
        sql = f"""
            UPDATE personas
            SET cuad_{dia}_man_min = ?, cuad_{dia}_tar_min = ?
            WHERE id = ?
            """
        execute_with_validation(cursor, sql, (man_min, tar_min, persona_id), "personas.update_cuadrante")
        self._connection.commit()

    def _sync_local_cuadrantes_from_personas(self) -> None:
        sync_local_cuadrantes_from_personas(self)

    def _persona_id_from_uuid(self, delegada_uuid: str | None) -> int | None:
        if not delegada_uuid:
            return None
        cursor = self._connection.cursor()
        cursor.execute("SELECT id FROM personas WHERE uuid = ?", (delegada_uuid,))
        row = cursor.fetchone()
        if not row:
            return None
        return row["id"]

    def _store_conflict(
        self, entity_type: str, uuid_value: str, local_snapshot: dict[str, Any], remote_snapshot: dict[str, Any]
    ) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO conflicts (uuid, entity_type, local_snapshot_json, remote_snapshot_json, detected_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                uuid_value,
                entity_type,
                json.dumps(local_snapshot, ensure_ascii=False),
                json.dumps(remote_snapshot, ensure_ascii=False),
                self._now_iso(),
            ),
        )
        self._connection.commit()

    def _rows_with_index(
        self,
        worksheet: Any,
        worksheet_name: str | None = None,
        aliases: dict[str, list[str]] | None = None,
    ) -> tuple[list[str], list[tuple[int, dict[str, Any]]]]:
        cache_name = worksheet_name or getattr(worksheet, "title", None)
        values = self._client.read_all_values(cache_name) if cache_name else worksheet.get_all_values()
        return rows_with_index(values, worksheet_name=cache_name or worksheet.title, aliases=aliases)

    def _header_map(self, headers: list[str], expected: list[str]) -> list[str]:
        if not headers:
            return expected
        missing = [col for col in expected if col not in headers]
        return headers + missing

    def _uuid_index(self, rows: list[tuple[int, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for _, row in rows:
            uuid_value = str(row.get("uuid", "")).strip()
            if uuid_value:
                index[uuid_value] = row
        return index

    def _update_row(self, worksheet: Any, row_number: int, headers: list[str], payload: dict[str, Any]) -> None:
        # Evita write-per-row: acumulamos updates y se ejecutan en un único batch_update por worksheet.
        row_values = [payload.get(header, "") for header in headers]
        range_name = f"A{row_number}:{rowcol_to_a1(row_number, len(headers))}"
        self._pending_batch_updates.setdefault(worksheet.title, []).append({"range": range_name, "values": [row_values]})

    def _append_row(self, worksheet: Any, headers: list[str], payload: dict[str, Any]) -> None:
        # Evita write-per-row: acumulamos altas y se ejecutan en un único append_rows por worksheet.
        row_values = [payload.get(header, "") for header in headers]
        self._pending_append_rows.setdefault(worksheet.title, []).append(row_values)


    def _reset_write_batch_state(self) -> None:
        self._pending_append_rows = {}
        self._pending_batch_updates = {}
        self._pending_values_batch_updates = {}

    def _queue_values_batch_update(self, worksheet: Any, row_number: int, col_idx: int, value: Any) -> None:
        a1_cell = rowcol_to_a1(row_number, col_idx)
        sheet_title = worksheet.title.replace("'", "''")
        range_name = f"'{sheet_title}'!{a1_cell}"
        self._pending_values_batch_updates.setdefault(worksheet.title, []).append({"range": range_name, "values": [[value]]})

    def _flush_write_batches(self, spreadsheet: Any, worksheet: Any) -> None:
        worksheet_title = worksheet.title
        appended_rows = self._pending_append_rows.pop(worksheet_title, [])
        updated_rows = self._pending_batch_updates.pop(worksheet_title, [])
        backfills = self._pending_values_batch_updates.pop(worksheet_title, [])

        if appended_rows:
            if hasattr(self._client, "append_rows"):
                self._client.append_rows(worksheet_title, appended_rows)
            else:
                worksheet.append_rows(appended_rows, value_input_option="USER_ENTERED")
            logger.info("Write batch (%s): %s rows appended", worksheet_title, len(appended_rows))

        if updated_rows:
            if hasattr(self._client, "batch_update"):
                self._client.batch_update(worksheet_title, updated_rows)
            else:
                worksheet.batch_update(updated_rows, value_input_option="USER_ENTERED")
            logger.info("Write batch (%s): %s rows updated", worksheet_title, len(updated_rows))

        if backfills:
            body = {"valueInputOption": "USER_ENTERED", "data": backfills}
            if hasattr(self._client, "values_batch_update"):
                self._client.values_batch_update(body)
            else:
                spreadsheet.values_batch_update(body)
            logger.info("Write batch: %s rows updated", len(backfills))

    def _log_sync_stats(self, operation: str) -> None:
        read_count = self._client.get_read_calls_count() if hasattr(self._client, "get_read_calls_count") else "n/a"
        write_count = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else "n/a"
        avoided = self._client.get_avoided_requests_count() if hasattr(self._client, "get_avoided_requests_count") else "n/a"
        logger.info(
            "Sync stats (%s): read_count=%s write_count=%s avoided_requests=%s",
            operation,
            read_count,
            write_count,
            avoided,
        )

    def _is_after_last_sync(self, updated_at: str | None, last_sync_at: str | None) -> bool:
        return sync_sheets_core.is_after_last_sync(updated_at, last_sync_at)

    def _is_conflict(
        self, local_updated_at: str | None, remote_updated_at: datetime | None, last_sync_at: str | None
    ) -> bool:
        return sync_sheets_core.is_conflict(local_updated_at, remote_updated_at, last_sync_at)

    def _is_remote_newer(self, local_updated_at: str | None, remote_updated_at: datetime | None) -> bool:
        return sync_sheets_core.is_remote_newer(local_updated_at, remote_updated_at)

    @staticmethod
    def _normalize_dia(dia: str) -> str | None:
        value = dia.strip().lower()
        mapping = {
            "lunes": "lun",
            "martes": "mar",
            "miercoles": "mie",
            "miércoles": "mie",
            "jueves": "jue",
            "viernes": "vie",
            "sabado": "sab",
            "sábado": "sab",
            "domingo": "dom",
        }
        if value in mapping:
            return mapping[value]
        if value in {"lun", "mar", "mie", "jue", "vie", "sab", "dom"}:
            return value
        return None

    @staticmethod
    def _int_or_zero(value: Any) -> int:
        return sync_sheets_core.int_or_zero(value)

    def _split_minutes(self, value: Any) -> tuple[int, int]:
        return sync_sheets_core.split_minutes(value)

    def _join_minutes(self, hours: Any, minutes: Any) -> int | None:
        return sync_sheets_core.join_minutes(hours, minutes)

    def _normalize_total_minutes(self, value: Any) -> int | None:
        return sync_sheets_core.normalize_total_minutes(value)

    def _normalize_hm_to_minutes(self, hours: Any, minutes: Any) -> int | None:
        return sync_sheets_core.normalize_hm_to_minutes(hours, minutes)

    @staticmethod
    def _parse_hhmm_to_minutes(value: Any) -> int | None:
        return sync_sheets_core.parse_hhmm_to_minutes(value)

    def _build_delegada_key(self, delegada_uuid: str | None, delegada_id: int | None) -> str | None:
        return sync_sheets_core.build_delegada_key(delegada_uuid, delegada_id)

    def _solicitud_dedupe_key(
        self,
        delegada_uuid: str | None,
        delegada_id: int | None,
        fecha_pedida: Any,
        completo: bool,
        horas_min: Any,
        desde_min: Any,
        hasta_min: Any,
    ) -> tuple[object, ...] | None:
        """Construye una clave estable para detectar solicitudes equivalentes.

        La clave ignora el UUID de la solicitud porque en sincronización pueden
        coexistir registros creados en dispositivos distintos para el mismo hecho
        de negocio. Se compara identidad funcional: delegada, fecha y tramo.
        """
        return sync_sheets_core.solicitud_dedupe_key(
            delegada_uuid,
            delegada_id,
            fecha_pedida,
            completo,
            horas_min,
            desde_min,
            hasta_min,
        )

    def _solicitud_dedupe_key_from_remote_row(self, row: dict[str, Any]) -> tuple[object, ...] | None:
        """Normaliza filas remotas heterogéneas al formato de deduplicación local."""
        return sync_sheets_core.solicitud_dedupe_key_from_remote_row(row)

    def _solicitud_dedupe_key_from_local_row(self, row: dict[str, Any]) -> tuple[object, ...] | None:
        """Deriva la misma clave de deduplicación desde el esquema SQLite local."""
        return sync_sheets_core.solicitud_dedupe_key_from_local_row(row)

    def _is_duplicate_local_solicitud(self, key: tuple[object, ...], exclude_uuid: str | None = None) -> bool:
        """Verifica si ya existe una solicitud equivalente activa en local.

        Se limita la búsqueda por delegada y fecha para reducir coste y evitar
        falsos positivos entre jornadas diferentes durante sincronizaciones masivas.
        """
        delegada_key, fecha_pedida, _, _, _, _ = key
        if not delegada_key or not fecha_pedida:
            return False
        cursor = self._connection.cursor()
        if delegada_key.startswith("uuid:"):
            delegada_uuid = delegada_key.removeprefix("uuid:")
            cursor.execute(
                """
                SELECT s.uuid, s.persona_id, p.uuid AS delegada_uuid, s.fecha_pedida,
                       s.desde_min, s.hasta_min, s.completo, s.horas_solicitadas_min
                FROM solicitudes s
                JOIN personas p ON p.id = s.persona_id
                WHERE p.uuid = ?
                  AND s.fecha_pedida = ?
                  AND (s.deleted = 0 OR s.deleted IS NULL)
                """,
                (delegada_uuid, fecha_pedida),
            )
        elif delegada_key.startswith("id:"):
            persona_id = self._int_or_zero(delegada_key.removeprefix("id:"))
            cursor.execute(
                """
                SELECT s.uuid, s.persona_id, p.uuid AS delegada_uuid, s.fecha_pedida,
                       s.desde_min, s.hasta_min, s.completo, s.horas_solicitadas_min
                FROM solicitudes s
                JOIN personas p ON p.id = s.persona_id
                WHERE s.persona_id = ?
                  AND s.fecha_pedida = ?
                  AND (s.deleted = 0 OR s.deleted IS NULL)
                """,
                (persona_id, fecha_pedida),
            )
        else:
            return False
        for row in cursor.fetchall():
            if exclude_uuid and row["uuid"] == exclude_uuid:
                continue
            local_key = self._solicitud_dedupe_key_from_local_row(dict(row))
            if local_key == key:
                return True
        return False

    @staticmethod
    def _parse_iso(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            text = str(value).replace("Z", "+00:00")
            return datetime.fromisoformat(text)
        except ValueError:
            return None

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
    def _format_rango_fechas(fechas: list[str]) -> str:
        fechas_filtradas = sorted({fecha for fecha in fechas if fecha})
        if not fechas_filtradas:
            return ""
        if len(fechas_filtradas) == 1:
            return fechas_filtradas[0]
        return f"{fechas_filtradas[0]} - {fechas_filtradas[-1]}"

    @staticmethod
    def _generate_uuid() -> str:
        return str(uuid.uuid4())
