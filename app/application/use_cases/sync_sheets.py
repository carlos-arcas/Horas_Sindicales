from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import gspread

from app.application.sheets_service import SHEETS_SCHEMA
from app.application.delegada_resolution import get_or_resolve_delegada_uuid
from app.application.sync_normalization import normalize_date, normalize_hhmm, solicitud_unique_key
from app.domain.ports import (
    SheetsClientPort,
    SheetsConfigStorePort,
    SheetsRepositoryPort,
)
from app.domain.sheets_errors import SheetsConfigError, SheetsRateLimitError
from app.domain.sync_models import SyncSummary

logger = logging.getLogger(__name__)


SOLICITUDES_HEADER_CANONICO = [
    "uuid",
    "delegada_uuid",
    "delegada_nombre",
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
]


def _execute_with_validation(cursor: sqlite3.Cursor, sql: str, params: tuple[object, ...], context: str) -> None:
    expected = sql.count("?")
    actual = len(params)
    if expected != actual:
        raise ValueError(
            f"SQL param mismatch for {context}: expected {expected} placeholders, got {actual} parameters."
        )
    cursor.execute(sql, params)



class SheetsSyncService:
    def __init__(
        self,
        connection: sqlite3.Connection,
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
        self._worksheet_cache: dict[str, gspread.Worksheet] = {}
        self._pending_append_rows: dict[str, list[list[Any]]] = {}
        self._pending_batch_updates: dict[str, list[dict[str, Any]]] = {}
        self._pending_values_batch_updates: dict[str, list[dict[str, Any]]] = {}
        self._enable_backfill = enable_backfill

    def pull(self) -> SyncSummary:
        spreadsheet = self._open_spreadsheet()
        self._prepare_sync_context(spreadsheet)
        self._repository.ensure_schema(spreadsheet, SHEETS_SCHEMA)
        summary = self._pull_with_spreadsheet(spreadsheet)
        self._log_sync_stats("pull")
        return summary

    def push(self) -> SyncSummary:
        spreadsheet = self._open_spreadsheet()
        self._prepare_sync_context(spreadsheet)
        self._repository.ensure_schema(spreadsheet, SHEETS_SCHEMA)
        summary = self._push_with_spreadsheet(spreadsheet)
        self._log_sync_stats("push")
        return summary

    def sync(self) -> SyncSummary:
        return self.sync_bidirectional()

    def sync_bidirectional(self) -> SyncSummary:
        spreadsheet = self._open_spreadsheet()
        self._prepare_sync_context(spreadsheet)
        self._repository.ensure_schema(spreadsheet, SHEETS_SCHEMA)
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

    def get_last_sync_at(self) -> str | None:
        return self._get_last_sync_at()

    def is_configured(self) -> bool:
        config = self._config_store.load()
        return bool(config and config.spreadsheet_id and config.credentials_path)

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

    def _prepare_sync_context(self, spreadsheet: gspread.Spreadsheet) -> None:
        self._worksheet_cache = {}
        try:
            self._worksheet_cache.update(self._client.get_worksheets_by_title())
        except SheetsRateLimitError:
            raise
        except Exception:
            logger.debug("No se pudo precargar metadata de worksheets; se continuará bajo demanda.", exc_info=True)

    def _get_worksheet(self, spreadsheet: gspread.Spreadsheet, worksheet_name: str) -> gspread.Worksheet:
        if worksheet_name in self._worksheet_cache:
            return self._worksheet_cache[worksheet_name]
        worksheet = self._client.get_worksheet(worksheet_name)
        self._worksheet_cache[worksheet_name] = worksheet
        return worksheet

    def _pull_with_spreadsheet(self, spreadsheet: gspread.Spreadsheet) -> SyncSummary:
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

    def _push_with_spreadsheet(self, spreadsheet: gspread.Spreadsheet) -> SyncSummary:
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

    def _open_spreadsheet(self) -> gspread.Spreadsheet:
        config = self._config_store.load()
        if not config or not config.spreadsheet_id or not config.credentials_path:
            raise SheetsConfigError("No hay configuración de Google Sheets.")
        credentials_path = Path(config.credentials_path)
        spreadsheet = self._client.open_spreadsheet(credentials_path, config.spreadsheet_id)
        return spreadsheet

    def _get_last_sync_at(self) -> str | None:
        cursor = self._connection.cursor()
        cursor.execute("SELECT last_sync_at FROM sync_state WHERE id = 1")
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

    def _pull_delegadas(self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None) -> tuple[int, int]:
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
        self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None, solicitud_titles: list[str] | None = None
    ) -> tuple[int, int, int, int, int]:
        downloaded = 0
        conflicts = 0
        omitted_duplicates = 0
        omitted_by_delegada = 0
        errors = 0
        for worksheet_name, worksheet in self._solicitudes_pull_sources(spreadsheet, solicitud_titles):
            headers, rows = self._rows_with_index(
                worksheet,
                worksheet_name,
                aliases=self._solicitudes_header_aliases(),
            )
            inserted_ws = 0
            updated_ws = 0
            sample_fecha_before: str | None = None
            sample_fecha_after: str | None = None
            logger.info("Pull solicitudes: worksheet=%s filas_leidas=%s", worksheet_name, len(rows))
            for row_number, raw_row in rows:
                if sample_fecha_before is None:
                    sample_fecha_before = str(raw_row.get("fecha") or raw_row.get("fecha_pedida") or "")
                row = self._normalize_remote_solicitud_row(raw_row, worksheet_name)
                if sample_fecha_after is None:
                    sample_fecha_after = str(row.get("fecha") or "")
                uuid_value = str(row.get("uuid", "")).strip()
                if not uuid_value:
                    existing = self._find_solicitud_by_composite_key(row)
                    if existing is not None:
                        omitted_duplicates += 1
                        uuid_value = str(existing["uuid"] or "").strip()
                    else:
                        uuid_value = self._generate_uuid()
                        inserted, omitted_delegada, insert_errors = self._insert_solicitud_from_remote(uuid_value, row)
                        downloaded += 1 if inserted else 0
                        inserted_ws += 1 if inserted else 0
                        omitted_by_delegada += omitted_delegada
                        errors += insert_errors
                    if self._enable_backfill:
                        self._backfill_uuid(worksheet, headers, row_number, "uuid", uuid_value)
                    continue
                remote_updated_at = self._parse_iso(row.get("updated_at"))
                local_row = self._fetch_solicitud(uuid_value)
                if local_row is None:
                    duplicate_key = self._solicitud_dedupe_key_from_remote_row(row)
                    if duplicate_key and self._is_duplicate_local_solicitud(duplicate_key, exclude_uuid=uuid_value):
                        logger.info(
                            "Omitiendo solicitud duplicada en pull. clave=%s registro=%s",
                            duplicate_key,
                            row,
                        )
                        omitted_duplicates += 1
                        continue
                    inserted, omitted_delegada, insert_errors = self._insert_solicitud_from_remote(uuid_value, row)
                    downloaded += 1 if inserted else 0
                    inserted_ws += 1 if inserted else 0
                    omitted_by_delegada += omitted_delegada
                    errors += insert_errors
                    continue
                if self._is_conflict(local_row["updated_at"], remote_updated_at, last_sync_at):
                    self._store_conflict("solicitudes", uuid_value, dict(local_row), row)
                    conflicts += 1
                    continue
                if self._is_remote_newer(local_row["updated_at"], remote_updated_at):
                    updated, omitted_delegada, update_errors = self._update_solicitud_from_remote(local_row["id"], row)
                    downloaded += 1 if updated else 0
                    updated_ws += 1 if updated else 0
                    omitted_by_delegada += omitted_delegada
                    errors += update_errors
            logger.info(
                "Pull solicitudes: worksheet=%s insertadas_local=%s actualizadas_local=%s",
                worksheet_name,
                inserted_ws,
                updated_ws,
            )
            logger.debug(
                "Pull solicitudes fechas: worksheet=%s ejemplo_antes='%s' ejemplo_despues='%s'",
                worksheet_name,
                sample_fecha_before or "",
                sample_fecha_after or "",
            )
            self._flush_write_batches(spreadsheet, worksheet)
        logger.info(
            "Pull solicitudes resumen: insertadas_local=%s omitidas_por_delegada=%s errores=%s",
            downloaded,
            omitted_by_delegada,
            errors,
        )
        return downloaded, conflicts, omitted_duplicates, omitted_by_delegada, errors

    @staticmethod
    def _solicitudes_header_aliases() -> dict[str, list[str]]:
        return {
            "uuid": ["id", "solicitud_uuid"],
            "delegada_uuid": ["delegado_uuid", "persona_uuid"],
            "delegada_nombre": ["delegada_nombre", "Delegada", "delegado_nombre", "delegada", "delegado", "persona_nombre", "nombre"],
            "fecha": ["fecha_pedida", "dia", "fecha solicitud"],
            "desde": ["desde_hora", "hora_desde"],
            "hasta": ["hasta_hora", "hora_hasta"],
            "completo": ["es_completo", "jornada_completa"],
            "horas": ["minutos_total", "horas_solicitadas", "total_minutos"],
            "notas": ["observaciones", "comentarios"],
        }

    def _solicitudes_pull_source_titles(self, spreadsheet: gspread.Spreadsheet) -> list[str]:
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
        self, spreadsheet: gspread.Spreadsheet, titles: list[str] | None = None
    ) -> list[tuple[str, gspread.Worksheet]]:
        selected_titles = titles or self._solicitudes_pull_source_titles(spreadsheet)
        return [(title, self._get_worksheet(spreadsheet, title)) for title in selected_titles]


    def _normalize_remote_solicitud_row(self, row: dict[str, Any], worksheet_name: str) -> dict[str, Any]:
        payload = dict(row)
        payload["fecha"] = self._normalize_date(row.get("fecha") or row.get("fecha_pedida")) or ""
        payload["created_at"] = self._normalize_date(row.get("created_at")) or payload["fecha"] or ""
        if row.get("minutos_total") in (None, "") and row.get("horas") not in (None, ""):
            payload["minutos_total"] = self._int_or_zero(row.get("horas"))

        if row.get("delegada_uuid") in (None, "") and row.get("delegado_uuid") not in (None, ""):
            payload["delegada_uuid"] = row.get("delegado_uuid")
        if row.get("delegada_nombre") in (None, ""):
            payload["delegada_nombre"] = row.get("delegada_nombre") or row.get("Delegada") or row.get("delegado_nombre") or row.get("delegada") or row.get("delegado") or ""

        desde_hhmm = self._remote_hhmm(
            row.get("desde_h"),
            row.get("desde_m"),
            row.get("desde") or row.get("hora_desde"),
        )
        hasta_hhmm = self._remote_hhmm(
            row.get("hasta_h"),
            row.get("hasta_m"),
            row.get("hasta") or row.get("hora_hasta"),
        )
        payload["desde_h"] = int(desde_hhmm.split(":")[0]) if desde_hhmm else ""
        payload["desde_m"] = int(desde_hhmm.split(":")[1]) if desde_hhmm else ""
        payload["hasta_h"] = int(hasta_hhmm.split(":")[0]) if hasta_hhmm else ""
        payload["hasta_m"] = int(hasta_hhmm.split(":")[1]) if hasta_hhmm else ""

        estado = str(row.get("estado", "")).strip().lower()
        payload["estado"] = estado
        if not estado and worksheet_name.strip().lower() in {"histórico", "historico"}:
            payload["estado"] = "historico"
        return payload

    @staticmethod
    def _remote_hhmm(hours: Any, minutes: Any, full_value: Any) -> str | None:
        full_text = normalize_hhmm(str(full_value).strip()) if full_value not in (None, "") else None
        if full_text:
            return full_text
        if hours in (None, "") and minutes in (None, ""):
            return None
        normalized = normalize_hhmm(f"{hours}:{minutes}")
        return normalized

    def _pull_cuadrantes(
        self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None
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

    def _pull_pdf_log(self, spreadsheet: gspread.Spreadsheet) -> int:
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

    def _pull_config(self, spreadsheet: gspread.Spreadsheet) -> int:
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

    def _push_pdf_log(self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None) -> int:
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

    def _push_config(self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None) -> int:
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
        self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None
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
        self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None
    ) -> tuple[int, int, int]:
        worksheet = self._get_worksheet(spreadsheet, "solicitudes")
        headers, rows = self._rows_with_index(worksheet)
        self._ensure_solicitudes_canonical_header(worksheet, headers)
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
        values: list[list[Any]] = [SOLICITUDES_HEADER_CANONICO]
        local_uuids: set[str] = set()
        for row in cursor.fetchall():
            if last_sync_at and not self._is_after_last_sync(row["updated_at"], last_sync_at):
                continue
            uuid_value = row["uuid"]
            local_uuids.add(uuid_value)
            remote_row = remote_index.get(uuid_value)
            remote_updated_at = self._parse_iso(remote_row.get("updated_at") if remote_row else None)
            if self._is_conflict(row["updated_at"], remote_updated_at, last_sync_at):
                self._store_conflict("solicitudes", uuid_value, dict(row), remote_row or {})
                conflicts += 1
                continue
            desde_h, desde_m = self._split_minutes(row["desde_min"])
            hasta_h, hasta_m = self._split_minutes(row["hasta_min"])
            values.append(
                [
                    uuid_value,
                    row["delegada_uuid"] or "",
                    row["delegada_nombre"] or "",
                    self._to_iso_date(row["fecha_pedida"]),
                    desde_h,
                    desde_m,
                    hasta_h,
                    hasta_m,
                    1 if row["completo"] else 0,
                    self._int_or_zero(row["horas_solicitadas_min"]),
                    row["notas"] or "",
                    "",
                    row["created_at"] or "",
                    row["updated_at"] or "",
                    row["source_device"] or self._device_id(),
                    self._int_or_zero(row["deleted"]),
                    row["pdf_hash"] or "",
                ]
            )
            uploaded += 1

        for _, remote_row in rows:
            remote_uuid = str(remote_row.get("uuid", "")).strip()
            if not remote_uuid or remote_uuid in local_uuids:
                continue
            desde_hhmm = self._remote_hhmm(remote_row.get("desde_h"), remote_row.get("desde_m"), remote_row.get("desde"))
            hasta_hhmm = self._remote_hhmm(remote_row.get("hasta_h"), remote_row.get("hasta_m"), remote_row.get("hasta"))
            desde_h = int(desde_hhmm.split(":")[0]) if desde_hhmm else 0
            desde_m = int(desde_hhmm.split(":")[1]) if desde_hhmm else 0
            hasta_h = int(hasta_hhmm.split(":")[0]) if hasta_hhmm else 0
            hasta_m = int(hasta_hhmm.split(":")[1]) if hasta_hhmm else 0
            values.append(
                [
                    remote_uuid,
                    remote_row.get("delegada_uuid") or remote_row.get("delegado_uuid") or "",
                    remote_row.get("delegada_nombre") or remote_row.get("delegado_nombre") or remote_row.get("Delegada") or "",
                    self._to_iso_date(remote_row.get("fecha") or remote_row.get("fecha_pedida")),
                    desde_h,
                    desde_m,
                    hasta_h,
                    hasta_m,
                    self._int_or_zero(remote_row.get("completo")),
                    self._int_or_zero(remote_row.get("minutos_total") or remote_row.get("horas")),
                    remote_row.get("notas") or "",
                    remote_row.get("estado") or "",
                    remote_row.get("created_at") or "",
                    remote_row.get("updated_at") or "",
                    remote_row.get("source_device") or "",
                    self._int_or_zero(remote_row.get("deleted")),
                    remote_row.get("pdf_id") or "",
                ]
            )
            omitted_duplicates += 1

        worksheet.update("A1", values)
        logger.info("PUSH Sheets: %s filas enviadas", max(len(values) - 1, 0))
        return uploaded, conflicts, omitted_duplicates

    def _ensure_solicitudes_canonical_header(self, worksheet: gspread.Worksheet, headers: list[str]) -> None:
        if headers == SOLICITUDES_HEADER_CANONICO:
            return
        logger.info("Normalizando encabezado de 'solicitudes' al formato canónico estable.")
        canonical_cols = len(SOLICITUDES_HEADER_CANONICO)
        current_cols = max(len(headers), canonical_cols)
        last_col = gspread.utils.rowcol_to_a1(1, current_cols)
        worksheet.batch_clear([f"A1:{last_col}"])
        worksheet.update("A1", [SOLICITUDES_HEADER_CANONICO])
        worksheet.resize(cols=canonical_cols)

    def _push_cuadrantes(
        self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None
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

    def _fetch_persona(self, uuid_value: str) -> sqlite3.Row | None:
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

    def _fetch_persona_by_nombre(self, nombre: str) -> sqlite3.Row | None:
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

    def _get_or_create_persona(self, row: dict[str, Any]) -> tuple[sqlite3.Row | None, bool, str | None]:
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

    def _find_solicitud_by_composite_key(self, row: dict[str, Any]) -> sqlite3.Row | None:
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

    def _backfill_uuid(self, worksheet: gspread.Worksheet, headers: list[str], row_number: int, column: str, value: str) -> None:
        if not self._enable_backfill or not value:
            return
        if column not in headers:
            return
        col_idx = headers.index(column) + 1
        # Evita write-per-row: acumulamos backfills y se ejecutan en un único values_batch_update por worksheet.
        self._queue_values_batch_update(worksheet, row_number, col_idx, value)

    def _fetch_solicitud(self, uuid_value: str) -> sqlite3.Row | None:
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

    def _fetch_cuadrante(self, uuid_value: str) -> sqlite3.Row | None:
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
        _execute_with_validation(
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
        _execute_with_validation(
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
        delegada_nombre = str(row.get("delegada_nombre") or "").strip()
        if not delegada_uuid:
            logger.warning(
                "Solicitud %s sin delegada_uuid. Intentando resolver por nombre='%s'",
                uuid_value,
                delegada_nombre,
            )
        resolved_uuid = get_or_resolve_delegada_uuid(self._connection, delegada_uuid, delegada_nombre)
        if not resolved_uuid:
            logger.warning("No resuelta -> omitida. Solicitud %s", uuid_value)
            return False, 1, 1
        persona_id = self._persona_id_from_uuid(resolved_uuid)
        if persona_id is None:
            logger.warning("No resuelta -> omitida. Solicitud %s", uuid_value)
            return False, 1, 1
        logger.info("Resuelta delegada: uuid_local=%s, nombre=%s", resolved_uuid, delegada_nombre)
        fecha_normalizada = self._normalize_date(row.get("fecha") or row.get("fecha_pedida"))
        created_normalizada = self._normalize_date(row.get("created_at")) or fecha_normalizada
        if not fecha_normalizada:
            logger.warning("Solicitud %s descartada por fecha inválida en pull: %s", uuid_value, row.get("fecha"))
            return False, 0, 1
        desde_min = self._join_minutes(row.get("desde_h"), row.get("desde_m"))
        hasta_min = self._join_minutes(row.get("hasta_h"), row.get("hasta_m"))
        _execute_with_validation(
            cursor,
            """
            INSERT INTO solicitudes (
                uuid, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash,
                created_at, updated_at, source_device, deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        delegada_nombre = str(row.get("delegada_nombre") or "").strip()
        if not delegada_uuid:
            logger.warning(
                "Solicitud %s sin delegada_uuid. Intentando resolver por nombre='%s'",
                row.get("uuid") or solicitud_id,
                delegada_nombre,
            )
        resolved_uuid = get_or_resolve_delegada_uuid(self._connection, delegada_uuid, delegada_nombre)
        if not resolved_uuid:
            logger.warning("No resuelta -> omitida. Solicitud %s", row.get("uuid") or solicitud_id)
            return False, 1, 1
        persona_id = self._persona_id_from_uuid(resolved_uuid)
        if persona_id is None:
            logger.warning("No resuelta -> omitida. Solicitud %s", row.get("uuid") or solicitud_id)
            return False, 1, 1
        logger.info("Resuelta delegada: uuid_local=%s, nombre=%s", resolved_uuid, delegada_nombre)
        fecha_normalizada = self._normalize_date(row.get("fecha") or row.get("fecha_pedida"))
        created_normalizada = self._normalize_date(row.get("created_at")) or fecha_normalizada
        if not fecha_normalizada:
            logger.warning("Solicitud id=%s no actualizada por fecha inválida en pull: %s", solicitud_id, row.get("fecha"))
            return False, 0, 1
        desde_min = self._join_minutes(row.get("desde_h"), row.get("desde_m"))
        hasta_min = self._join_minutes(row.get("hasta_h"), row.get("hasta_m"))
        _execute_with_validation(
            cursor,
            """
            UPDATE solicitudes
            SET persona_id = ?, fecha_pedida = ?, desde_min = ?, hasta_min = ?, completo = ?,
                horas_solicitadas_min = ?, notas = ?, pdf_hash = ?, created_at = ?, updated_at = ?,
                source_device = ?, deleted = ?
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
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%y", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    @staticmethod
    def _to_iso_date(value: Any) -> str:
        if not value:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        text = str(value).strip()
        normalized = SheetsSyncService._normalize_date(text)
        if normalized:
            return normalized
        if "-" in text:
            return text
        return text

    def _minutes_to_hhmm(self, value: Any) -> str:
        hours, minutes = self._split_minutes(value)
        return f"{hours:02d}:{minutes:02d}"

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
        _execute_with_validation(cursor, sql, (man_min, tar_min, persona_id), "personas.update_cuadrante")
        self._connection.commit()

    def _sync_local_cuadrantes_from_personas(self) -> None:
        cursor = self._connection.cursor()
        cursor.execute("PRAGMA table_info(personas)")
        persona_columns = {row[1] for row in cursor.fetchall()}
        has_updated_at = "updated_at" in persona_columns
        cursor.execute("SELECT uuid, id FROM personas")
        personas = cursor.fetchall()
        for persona in personas:
            persona_uuid = persona["uuid"]
            if not persona_uuid:
                persona_uuid = self._generate_uuid()
                now_iso = self._now_iso()
                if has_updated_at:
                    cursor.execute(
                        "UPDATE personas SET uuid = ?, updated_at = ? WHERE id = ?",
                        (persona_uuid, now_iso, persona["id"]),
                    )
                else:
                    cursor.execute(
                        "UPDATE personas SET uuid = ? WHERE id = ?",
                        (persona_uuid, persona["id"]),
                    )
                logger.warning(
                    "Persona sin uuid encontrada (id=%s). Se generó un uuid nuevo para sincronización.",
                    persona["id"],
                )
            cursor.execute(
                """
                SELECT uuid, dia_semana, man_min, tar_min, updated_at FROM cuadrantes WHERE delegada_uuid = ?
                """,
                (persona_uuid,),
            )
            existing = {row["dia_semana"]: row for row in cursor.fetchall()}
            for dia in ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]:
                man_min = self._get_persona_minutes(persona["id"], dia, "man")
                tar_min = self._get_persona_minutes(persona["id"], dia, "tar")
                existing_row = existing.get(dia)
                if existing_row:
                    if (
                        existing_row["man_min"] == man_min
                        and existing_row["tar_min"] == tar_min
                        and existing_row["updated_at"]
                    ):
                        continue
                    cursor.execute(
                        """
                        UPDATE cuadrantes
                        SET man_min = ?, tar_min = ?, updated_at = ?
                        WHERE uuid = ?
                        """,
                        (man_min, tar_min, self._now_iso(), existing_row["uuid"]),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO cuadrantes (uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, deleted)
                        VALUES (?, ?, ?, ?, ?, ?, 0)
                        """,
                        (self._generate_uuid(), persona_uuid, dia, man_min, tar_min, self._now_iso()),
                    )
        self._connection.commit()

    def _get_persona_minutes(self, persona_id: int, dia: str, segmento: str) -> int:
        cursor = self._connection.cursor()
        cursor.execute(
            f"SELECT cuad_{dia}_{segmento}_min AS value FROM personas WHERE id = ?",
            (persona_id,),
        )
        row = cursor.fetchone()
        return row["value"] if row and row["value"] is not None else 0

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
        worksheet: gspread.Worksheet,
        worksheet_name: str | None = None,
        aliases: dict[str, list[str]] | None = None,
    ) -> tuple[list[str], list[tuple[int, dict[str, Any]]]]:
        cache_name = worksheet_name or getattr(worksheet, "title", None)
        if cache_name:
            values = self._client.read_all_values(cache_name)
        else:
            values = worksheet.get_all_values()
        if not values:
            return [], []
        headers = values[0]
        canonical_by_header: dict[str, str] = {}
        if aliases:
            lowered_map: dict[str, str] = {}
            for canonical, names in aliases.items():
                lowered_map[canonical.strip().lower()] = canonical
                for name in names:
                    lowered_map[name.strip().lower()] = canonical
            for header in headers:
                key = str(header).strip().lower()
                canonical_by_header[header] = lowered_map.get(key, header)
        rows: list[tuple[int, dict[str, Any]]] = []
        for row_number, row in enumerate(values[1:], start=2):
            if not any(str(cell).strip() for cell in row):
                continue
            payload = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            if canonical_by_header:
                canonical_payload: dict[str, Any] = {}
                for original_key, value in payload.items():
                    canonical_key = canonical_by_header.get(original_key, original_key)
                    if canonical_key not in canonical_payload or not str(canonical_payload.get(canonical_key, "")).strip():
                        canonical_payload[canonical_key] = value
                payload = canonical_payload
            payload["__row_number__"] = row_number
            rows.append((row_number, payload))
        logger.info("Read worksheet=%s filas_leidas=%s", cache_name or worksheet.title, len(rows))
        return headers, rows

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

    def _update_row(self, worksheet: gspread.Worksheet, row_number: int, headers: list[str], payload: dict[str, Any]) -> None:
        # Evita write-per-row: acumulamos updates y se ejecutan en un único batch_update por worksheet.
        row_values = [payload.get(header, "") for header in headers]
        range_name = f"A{row_number}:{gspread.utils.rowcol_to_a1(row_number, len(headers))}"
        self._pending_batch_updates.setdefault(worksheet.title, []).append({"range": range_name, "values": [row_values]})

    def _append_row(self, worksheet: gspread.Worksheet, headers: list[str], payload: dict[str, Any]) -> None:
        # Evita write-per-row: acumulamos altas y se ejecutan en un único append_rows por worksheet.
        row_values = [payload.get(header, "") for header in headers]
        self._pending_append_rows.setdefault(worksheet.title, []).append(row_values)


    def _reset_write_batch_state(self) -> None:
        self._pending_append_rows = {}
        self._pending_batch_updates = {}
        self._pending_values_batch_updates = {}

    def _queue_values_batch_update(self, worksheet: gspread.Worksheet, row_number: int, col_idx: int, value: Any) -> None:
        a1_cell = gspread.utils.rowcol_to_a1(row_number, col_idx)
        sheet_title = worksheet.title.replace("'", "''")
        range_name = f"'{sheet_title}'!{a1_cell}"
        self._pending_values_batch_updates.setdefault(worksheet.title, []).append({"range": range_name, "values": [[value]]})

    def _flush_write_batches(self, spreadsheet: gspread.Spreadsheet, worksheet: gspread.Worksheet) -> None:
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
        if not updated_at:
            return False
        if not last_sync_at:
            return True
        parsed_updated = self._parse_iso(updated_at)
        parsed_last = self._parse_iso(last_sync_at)
        if not parsed_updated or not parsed_last:
            return False
        return parsed_updated > parsed_last

    def _is_conflict(
        self, local_updated_at: str | None, remote_updated_at: datetime | None, last_sync_at: str | None
    ) -> bool:
        if not local_updated_at or not remote_updated_at or not last_sync_at:
            return False
        parsed_local = self._parse_iso(local_updated_at)
        parsed_last = self._parse_iso(last_sync_at)
        if not parsed_local or not parsed_last:
            return False
        return parsed_local > parsed_last and remote_updated_at > parsed_last

    def _is_remote_newer(self, local_updated_at: str | None, remote_updated_at: datetime | None) -> bool:
        if not remote_updated_at:
            return False
        if not local_updated_at:
            return True
        parsed_local = self._parse_iso(local_updated_at)
        if not parsed_local:
            return True
        return remote_updated_at > parsed_local

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
        try:
            if value is None or value == "":
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    def _split_minutes(self, value: Any) -> tuple[int, int]:
        minutes = self._int_or_zero(value)
        return minutes // 60, minutes % 60

    def _join_minutes(self, hours: Any, minutes: Any) -> int | None:
        if hours is None and minutes is None:
            return None
        return self._int_or_zero(hours) * 60 + self._int_or_zero(minutes)

    def _normalize_total_minutes(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        return self._int_or_zero(value)

    def _normalize_hm_to_minutes(self, hours: Any, minutes: Any) -> int | None:
        if hours is None and minutes is None:
            return None
        parsed = self._parse_hhmm_to_minutes(hours)
        if parsed is not None:
            return parsed
        return self._int_or_zero(hours) * 60 + self._int_or_zero(minutes)

    @staticmethod
    def _parse_hhmm_to_minutes(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, str) and ":" in value:
            parts = value.strip().split(":")
            if len(parts) >= 2:
                try:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                except ValueError:
                    return None
                return hours * 60 + minutes
        return None

    def _build_delegada_key(self, delegada_uuid: str | None, delegada_id: int | None) -> str | None:
        uuid_value = (delegada_uuid or "").strip()
        if uuid_value:
            return f"uuid:{uuid_value}"
        if delegada_id is None:
            return None
        return f"id:{delegada_id}"

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
        delegada_key = self._build_delegada_key(delegada_uuid, delegada_id)
        if not delegada_key or not fecha_pedida:
            return None
        minutos_total = self._int_or_zero(horas_min)
        if completo:
            return (delegada_key, str(fecha_pedida), True, minutos_total, None, None)
        desde_value = self._normalize_total_minutes(desde_min)
        hasta_value = self._normalize_total_minutes(hasta_min)
        return (
            delegada_key,
            str(fecha_pedida),
            False,
            minutos_total,
            desde_value,
            hasta_value,
        )

    def _solicitud_dedupe_key_from_remote_row(self, row: dict[str, Any]) -> tuple[object, ...] | None:
        """Normaliza filas remotas heterogéneas al formato de deduplicación local."""
        delegada_uuid = str(row.get("delegada_uuid", "")).strip() or None
        delegada_id = None
        if row.get("delegada_id") not in (None, ""):
            delegada_id = self._int_or_zero(row.get("delegada_id"))
        fecha_pedida = row.get("fecha") or row.get("fecha_pedida")
        completo = bool(self._int_or_zero(row.get("completo")))
        horas_min = row.get("minutos_total") or row.get("horas_solicitadas_min")
        desde_min = self._normalize_hm_to_minutes(row.get("desde_h"), row.get("desde_m"))
        hasta_min = self._normalize_hm_to_minutes(row.get("hasta_h"), row.get("hasta_m"))
        return self._solicitud_dedupe_key(
            delegada_uuid,
            delegada_id,
            fecha_pedida,
            completo,
            horas_min,
            desde_min,
            hasta_min,
        )

    def _solicitud_dedupe_key_from_local_row(self, row: dict[str, Any]) -> tuple[object, ...] | None:
        """Deriva la misma clave de deduplicación desde el esquema SQLite local."""
        delegada_uuid = row.get("delegada_uuid")
        delegada_id = row.get("persona_id")
        fecha_pedida = row.get("fecha_pedida")
        completo = bool(row.get("completo"))
        horas_min = row.get("horas_solicitadas_min")
        return self._solicitud_dedupe_key(
            delegada_uuid,
            delegada_id,
            fecha_pedida,
            completo,
            horas_min,
            row.get("desde_min"),
            row.get("hasta_min"),
        )

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
