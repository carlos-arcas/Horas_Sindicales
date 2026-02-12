from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gspread

from app.application.sheets_service import SHEETS_SCHEMA
from app.application.sync_normalization import normalize_date, normalize_hhmm, solicitud_unique_key
from app.domain.ports import (
    SheetsClientPort,
    SheetsConfigStorePort,
    SheetsRepositoryPort,
)
from app.domain.sheets_errors import SheetsConfigError
from app.domain.sync_models import SyncSummary

logger = logging.getLogger(__name__)


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
    ) -> None:
        self._connection = connection
        self._config_store = config_store
        self._client = client
        self._repository = repository

    def pull(self) -> SyncSummary:
        spreadsheet = self._open_spreadsheet()
        self._repository.ensure_schema(spreadsheet, SHEETS_SCHEMA)
        last_sync_at = self._get_last_sync_at()
        downloaded = 0
        conflicts = 0
        omitted_duplicates = 0
        downloaded_count, conflict_count = self._pull_delegadas(spreadsheet, last_sync_at)
        downloaded += downloaded_count
        conflicts += conflict_count
        downloaded_count, conflict_count, duplicate_count = self._pull_solicitudes(spreadsheet, last_sync_at)
        downloaded += downloaded_count
        conflicts += conflict_count
        omitted_duplicates += duplicate_count
        downloaded_count, conflict_count = self._pull_cuadrantes(spreadsheet, last_sync_at)
        downloaded += downloaded_count
        conflicts += conflict_count
        downloaded += self._pull_pdf_log(spreadsheet)
        downloaded += self._pull_config(spreadsheet)
        return SyncSummary(
            inserted_local=downloaded,
            updated_local=0,
            duplicates_skipped=omitted_duplicates,
            conflicts_detected=conflicts,
        )

    def push(self) -> SyncSummary:
        spreadsheet = self._open_spreadsheet()
        self._repository.ensure_schema(spreadsheet, SHEETS_SCHEMA)
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
        return SyncSummary(
            inserted_remote=uploaded,
            updated_remote=0,
            duplicates_skipped=omitted_duplicates,
            conflicts_detected=conflicts,
        )

    def sync(self) -> SyncSummary:
        return self.sync_bidirectional()

    def sync_bidirectional(self) -> SyncSummary:
        pull_summary = self.pull()
        push_summary = self.push()
        return SyncSummary(
            inserted_local=pull_summary.inserted_local,
            updated_local=pull_summary.updated_local,
            inserted_remote=push_summary.inserted_remote,
            updated_remote=push_summary.updated_remote,
            duplicates_skipped=pull_summary.duplicates_skipped + push_summary.duplicates_skipped,
            conflicts_detected=pull_summary.conflicts_detected + push_summary.conflicts_detected,
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
        worksheet = spreadsheet.worksheet("delegadas")
        headers, rows = self._rows_with_index(worksheet)
        downloaded = 0
        conflicts = 0
        for row_number, row in rows:
            nombre_value = str(row.get("nombre", "")).strip()
            uuid_value = str(row.get("uuid", "")).strip()
            if not uuid_value and not nombre_value:
                logger.warning("Fila delegada sin uuid ni nombre; se omite: %s", row)
                continue
            local_row, was_inserted, persona_uuid = self._get_or_create_persona(row)
            if not str(row.get("uuid", "")).strip() and persona_uuid:
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
        return downloaded, conflicts

    def _pull_solicitudes(
        self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None
    ) -> tuple[int, int, int]:
        worksheet = spreadsheet.worksheet("solicitudes")
        headers, rows = self._rows_with_index(worksheet)
        downloaded = 0
        conflicts = 0
        omitted_duplicates = 0
        for row_number, row in rows:
            uuid_value = str(row.get("uuid", "")).strip()
            if not uuid_value:
                existing = self._find_solicitud_by_composite_key(row)
                if existing is not None:
                    omitted_duplicates += 1
                    uuid_value = str(existing["uuid"] or "").strip()
                else:
                    uuid_value = self._generate_uuid()
                    self._insert_solicitud_from_remote(uuid_value, row)
                    downloaded += 1
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
                self._insert_solicitud_from_remote(uuid_value, row)
                downloaded += 1
                continue
            if self._is_conflict(local_row["updated_at"], remote_updated_at, last_sync_at):
                self._store_conflict("solicitudes", uuid_value, dict(local_row), row)
                conflicts += 1
                continue
            if self._is_remote_newer(local_row["updated_at"], remote_updated_at):
                self._update_solicitud_from_remote(local_row["id"], row)
                downloaded += 1
        return downloaded, conflicts, omitted_duplicates

    def _pull_cuadrantes(
        self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None
    ) -> tuple[int, int]:
        worksheet = spreadsheet.worksheet("cuadrantes")
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
        worksheet = spreadsheet.worksheet("pdf_log")
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
        worksheet = spreadsheet.worksheet("config")
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
        worksheet = spreadsheet.worksheet("pdf_log")
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
                row_number = remote_row["__row_number__"]
                self._update_row(worksheet, row_number, header_map, payload)
            else:
                self._append_row(worksheet, header_map, payload)
            uploaded += 1
        return uploaded

    def _push_config(self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None) -> int:
        worksheet = spreadsheet.worksheet("config")
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
                row_number = remote_row["__row_number__"]
                self._update_row(worksheet, row_number, header_map, payload)
            else:
                self._append_row(worksheet, header_map, payload)
            uploaded += 1
        return uploaded

    def _push_delegadas(
        self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None
    ) -> tuple[int, int]:
        worksheet = spreadsheet.worksheet("delegadas")
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
                row_number = remote_row["__row_number__"]
                self._update_row(worksheet, row_number, header_map, payload)
            else:
                self._append_row(worksheet, header_map, payload)
            uploaded += 1
        return uploaded, conflicts

    def _push_solicitudes(
        self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None
    ) -> tuple[int, int, int]:
        worksheet = spreadsheet.worksheet("solicitudes")
        headers, rows = self._rows_with_index(worksheet)
        header_map = self._header_map(headers, SHEETS_SCHEMA["solicitudes"])
        remote_index = self._uuid_index(rows)
        remote_dedupe_index: dict[tuple[object, ...], dict[str, Any]] = {}
        for _, row in rows:
            key = self._solicitud_dedupe_key_from_remote_row(row)
            if key:
                remote_dedupe_index.setdefault(key, row)
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
        for row in cursor.fetchall():
            if not self._is_after_last_sync(row["updated_at"], last_sync_at):
                continue
            uuid_value = row["uuid"]
            remote_row = remote_index.get(uuid_value)
            remote_updated_at = self._parse_iso(remote_row.get("updated_at") if remote_row else None)
            if self._is_conflict(row["updated_at"], remote_updated_at, last_sync_at):
                self._store_conflict("solicitudes", uuid_value, dict(row), remote_row or {})
                conflicts += 1
                continue
            if not remote_row:
                local_key = self._solicitud_dedupe_key_from_local_row(dict(row))
                if local_key and local_key in remote_dedupe_index:
                    logger.info(
                        "Omitiendo solicitud duplicada en push. clave=%s registro_local=%s registro_remoto=%s",
                        local_key,
                        dict(row),
                        remote_dedupe_index[local_key],
                    )
                    omitted_duplicates += 1
                    continue
            desde_h, desde_m = self._split_minutes(row["desde_min"])
            hasta_h, hasta_m = self._split_minutes(row["hasta_min"])
            payload = {
                "uuid": uuid_value,
                "delegada_uuid": row["delegada_uuid"],
                "Delegada": row["delegada_nombre"] or "",
                "fecha": row["fecha_pedida"],
                "desde_h": desde_h,
                "desde_m": desde_m,
                "hasta_h": hasta_h,
                "hasta_m": hasta_m,
                "completo": 1 if row["completo"] else 0,
                "minutos_total": row["horas_solicitadas_min"] or 0,
                "notas": row["notas"] or "",
                "estado": "",
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "source_device": row["source_device"] or self._device_id(),
                "deleted": row["deleted"] or 0,
                "pdf_id": row["pdf_hash"] or "",
            }
            if remote_row:
                row_number = remote_row["__row_number__"]
                self._update_row(worksheet, row_number, header_map, payload)
            else:
                self._append_row(worksheet, header_map, payload)
            uploaded += 1
        return uploaded, conflicts, omitted_duplicates

    def _push_cuadrantes(
        self, spreadsheet: gspread.Spreadsheet, last_sync_at: str | None
    ) -> tuple[int, int]:
        worksheet = spreadsheet.worksheet("cuadrantes")
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
                row_number = remote_row["__row_number__"]
                self._update_row(worksheet, row_number, header_map, payload)
            else:
                self._append_row(worksheet, header_map, payload)
            uploaded += 1
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
        fecha = normalize_date(str(row.get("fecha", "")))
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
        if not value:
            return
        if column not in headers:
            return
        col_idx = headers.index(column) + 1
        if hasattr(worksheet, "update_cell"):
            worksheet.update_cell(row_number, col_idx, value)
            return
        if hasattr(worksheet, "_values"):
            values = getattr(worksheet, "_values")
            while len(values) < row_number:
                values.append([""] * len(headers))
            while len(values[row_number - 1]) < col_idx:
                values[row_number - 1].append("")
            values[row_number - 1][col_idx - 1] = value

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

    def _insert_solicitud_from_remote(self, uuid_value: str, row: dict[str, Any]) -> None:
        cursor = self._connection.cursor()
        persona_id = self._persona_id_from_uuid(row.get("delegada_uuid"))
        if persona_id is None:
            logger.warning("Delegada %s no encontrada al importar solicitud %s", row.get("delegada_uuid"), uuid_value)
            return
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
                row.get("created_at") or row.get("fecha"),
                row.get("fecha"),
                desde_min,
                hasta_min,
                1 if self._int_or_zero(row.get("completo")) else 0,
                self._int_or_zero(row.get("minutos_total")),
                None,
                row.get("notas") or "",
                None,
                row.get("pdf_id"),
                row.get("created_at") or row.get("fecha"),
                row.get("updated_at") or self._now_iso(),
                row.get("source_device"),
                self._int_or_zero(row.get("deleted")),
            ),
            "solicitudes.insert_remote",
        )
        self._connection.commit()

    def _update_solicitud_from_remote(self, solicitud_id: int, row: dict[str, Any]) -> None:
        cursor = self._connection.cursor()
        persona_id = self._persona_id_from_uuid(row.get("delegada_uuid"))
        if persona_id is None:
            logger.warning("Delegada %s no encontrada al actualizar solicitud %s", row.get("delegada_uuid"), row)
            return
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
                row.get("fecha"),
                desde_min,
                hasta_min,
                1 if self._int_or_zero(row.get("completo")) else 0,
                self._int_or_zero(row.get("minutos_total")),
                row.get("notas") or "",
                row.get("pdf_id"),
                row.get("created_at") or row.get("fecha"),
                row.get("updated_at") or self._now_iso(),
                row.get("source_device"),
                self._int_or_zero(row.get("deleted")),
                solicitud_id,
            ),
            "solicitudes.update_remote",
        )
        self._connection.commit()

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

    def _rows_with_index(self, worksheet: gspread.Worksheet) -> tuple[list[str], list[tuple[int, dict[str, Any]]]]:
        values = worksheet.get_all_values()
        if not values:
            return [], []
        headers = values[0]
        rows: list[tuple[int, dict[str, Any]]] = []
        for row_number, row in enumerate(values[1:], start=2):
            if not any(str(cell).strip() for cell in row):
                continue
            payload = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            payload["__row_number__"] = row_number
            rows.append((row_number, payload))
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
        row_values = [payload.get(header, "") for header in headers]
        worksheet.update(f"A{row_number}:{gspread.utils.rowcol_to_a1(row_number, len(headers))}", [row_values])

    def _append_row(self, worksheet: gspread.Worksheet, headers: list[str], payload: dict[str, Any]) -> None:
        row_values = [payload.get(header, "") for header in headers]
        worksheet.append_row(row_values, value_input_option="USER_ENTERED")

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
